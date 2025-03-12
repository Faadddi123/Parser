from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import os
import xml.etree.ElementTree as ET
import requests
import time
import uuid
import tempfile
import random
from werkzeug.utils import secure_filename

# Try to import Google Translate API
try:
    from google.cloud import translate_v2 as google_translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'xml_translator_uploads')
ALLOWED_EXTENSIONS = {'xml'}
DEFAULT_SRC_LANG = "en"
DEFAULT_TARGET_LANG = "ru"
DEFAULT_FIELDS_TO_TRANSLATE = ["strName", "strDesc"]
DEFAULT_API = "libretranslate"  # Changed default to LibreTranslate
DEFAULT_MYMEMORY_API_URL = "https://api.mymemory.translated.net/get"

# Multiple LibreTranslate instances to try
LIBRETRANSLATE_INSTANCES = [
    "https://libretranslate.de",
    "https://translate.argosopentech.com",
    "https://translate.terraprint.co",
    "https://lt.vern.cc"
]

# Get a random instance to distribute load
def get_libretranslate_instance():
    return random.choice(LIBRETRANSLATE_INSTANCES)

DEFAULT_LIBRETRANSLATE_URL = f"{get_libretranslate_instance()}/translate"
LIBRETRANSLATE_LANGUAGES_URL = f"{get_libretranslate_instance()}/languages"

# Request timeout settings
REQUEST_TIMEOUT = 10  # 10 seconds timeout for API requests
MAX_RETRIES = 2      # Maximum retries for failed API requests

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def translate_with_mymemory(text, src_lang, target_lang, api_url=DEFAULT_MYMEMORY_API_URL):
    """Translate text using MyMemory Translation API."""
    if not text or text.strip() == "":
        return text
    
    params = {
        'q': text,
        'langpair': f'{src_lang}|{target_lang}'
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=REQUEST_TIMEOUT)
        response_json = response.json()
        
        if response.status_code == 200 and response_json['responseStatus'] == 200:
            translated_text = response_json['responseData']['translatedText']
            return translated_text
        else:
            app.logger.error(f"Translation error: {response_json.get('responseDetails', 'Unknown error')}")
            return text
    except Exception as e:
        app.logger.error(f"Error during translation: {str(e)}")
        return text

def translate_with_libretranslate(text, src_lang, target_lang, retry_count=0):
    """Translate text using LibreTranslate API with retries and fallbacks."""
    if not text or text.strip() == "":
        return text
    
    # If we've reached max retries, fall back to MyMemory
    if retry_count > MAX_RETRIES:
        app.logger.warning("LibreTranslate failed after maximum retries, falling back to MyMemory")
        return translate_with_mymemory(text, src_lang, target_lang)
    
    # Select a different instance on each retry
    instance = LIBRETRANSLATE_INSTANCES[retry_count % len(LIBRETRANSLATE_INSTANCES)]
    api_url = f"{instance}/translate"
    
    payload = {
        "q": text,
        "source": src_lang,
        "target": target_lang,
        "format": "text"
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=REQUEST_TIMEOUT)
        response_json = response.json()
        
        if response.status_code == 200 and "translatedText" in response_json:
            return response_json["translatedText"]
        else:
            error_msg = response_json.get('error', 'Unknown error')
            app.logger.error(f"LibreTranslate error from {instance}: {error_msg}")
            
            # Try another instance
            return translate_with_libretranslate(text, src_lang, target_lang, retry_count + 1)
    except Exception as e:
        app.logger.error(f"Error during LibreTranslate translation from {instance}: {str(e)}")
        
        # Try another instance
        return translate_with_libretranslate(text, src_lang, target_lang, retry_count + 1)

def translate_with_google(text, src_lang, target_lang):
    """Translate text using Google Translate API."""
    if not text or text.strip() == "":
        return text
    
    try:
        translate_client = google_translate.Client()
        result = translate_client.translate(
            text, 
            target_language=target_lang,
            source_language=src_lang
        )
        
        translated_text = result['translatedText']
        return translated_text
    except Exception as e:
        app.logger.error(f"Error during Google translation: {str(e)}")
        return text

def translate_text(text, src_lang, target_lang, api="libretranslate"):
    """Translate text using the specified API."""
    if not text or text.strip() == "":
        return text
    
    # Replace XML entities to prevent translation issues
    text = text.replace("&lt;", "<LESSTHAN>").replace("&gt;", "<GREATERTHAN>")
    
    if api == "google" and GOOGLE_TRANSLATE_AVAILABLE:
        translated_text = translate_with_google(text, src_lang, target_lang)
    elif api == "libretranslate":
        translated_text = translate_with_libretranslate(text, src_lang, target_lang)
    else:
        translated_text = translate_with_mymemory(text, src_lang, target_lang)
    
    # Restore XML entities
    translated_text = translated_text.replace("<LESSTHAN>", "&lt;").replace("<GREATERTHAN>", "&gt;")
    return translated_text

def translate_xml(xml_content, src_lang, target_lang, fields_to_translate, api="libretranslate"):
    """Parse XML content, translate specified fields, and return the translated XML content."""
    result = {
        'success': True,
        'message': '',
        'translated_count': 0,
        'translated_xml': None,
        'api_used': api  # Track which API was actually used
    }
    
    try:
        # Create a temporary file to write the XML content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as temp_file:
            temp_filename = temp_file.name
            temp_file.write(xml_content.encode('utf-8'))
        
        # Parse XML
        tree = ET.parse(temp_filename)
        root = tree.getroot()
        
        # Count elements that need translation
        elements_to_translate = []
        for table in root.findall(".//table"):
            for column in table.findall("column"):
                if column.get("name") in fields_to_translate and column.text:
                    elements_to_translate.append(column)
        
        if not elements_to_translate:
            result['message'] = 'No text found to translate in the XML file.'
            return result
        
        result['translated_count'] = len(elements_to_translate)
        
        # Translate elements with batch processing to avoid timeouts
        batch_size = 5  # Process 5 elements at a time
        for i in range(0, len(elements_to_translate), batch_size):
            batch = elements_to_translate[i:i+batch_size]
            
            # Process each item in the batch
            for column in batch:
                if column.text:
                    original_text = column.text
                    translated_text = translate_text(original_text, src_lang, target_lang, api)
                    
                    # If LibreTranslate failed and fell back to MyMemory, record this
                    if api == "libretranslate" and translated_text == original_text:
                        # Try explicitly with MyMemory as fallback
                        fallback_text = translate_with_mymemory(original_text, src_lang, target_lang)
                        if fallback_text != original_text:
                            translated_text = fallback_text
                            result['api_used'] = "mymemory (fallback)"
                    
                    column.text = translated_text
            
            # Add a delay between batches to avoid rate limiting
            if i + batch_size < len(elements_to_translate):
                time.sleep(0.5)
        
        # Write the translated XML to a temporary file
        tree.write(temp_filename, encoding="utf-8", xml_declaration=True)
        
        # Read the translated XML content
        with open(temp_filename, 'r', encoding='utf-8') as f:
            translated_xml = f.read()
        
        result['translated_xml'] = translated_xml
        result['message'] = f'Successfully translated {len(elements_to_translate)} elements.'
        
        # Clean up temporary file
        os.unlink(temp_filename)
        
    except Exception as e:
        result['success'] = False
        result['message'] = f'Error processing XML: {str(e)}'
        
    return result

@app.route('/')
def index():
    google_available = GOOGLE_TRANSLATE_AVAILABLE
    return render_template('index.html', google_available=google_available)

@app.route('/translate', methods=['POST'])
def translate():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Get form data
        src_lang = request.form.get('src_lang', DEFAULT_SRC_LANG)
        target_lang = request.form.get('target_lang', DEFAULT_TARGET_LANG)
        api = request.form.get('api', DEFAULT_API)
        fields = request.form.getlist('fields') or DEFAULT_FIELDS_TO_TRANSLATE
        
        # Check if XML file is valid
        try:
            xml_content = file.read().decode('utf-8')
            ET.fromstring(xml_content)
        except Exception as e:
            flash(f'Invalid XML file: {str(e)}')
            return redirect(url_for('index'))
        
        # Generate a unique ID for this translation
        translation_id = str(uuid.uuid4())
        
        # Store file and preferences in session
        session['translation'] = {
            'id': translation_id,
            'filename': secure_filename(file.filename),
            'src_lang': src_lang,
            'target_lang': target_lang,
            'api': api,
            'fields': fields
        }
        
        # Save XML content to a temporary file
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{translation_id}_original.xml")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        
        # Translate XML
        result = translate_xml(xml_content, src_lang, target_lang, fields, api)
        
        if result['success']:
            # Save translated XML
            output_translated_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{translation_id}_translated.xml")
            with open(output_translated_path, 'w', encoding='utf-8') as f:
                f.write(result['translated_xml'])
            
            session['translation']['translated_path'] = output_translated_path
            session['translation']['message'] = result['message']
            session['translation']['count'] = result['translated_count']
            
            # Record which API was actually used (in case of fallback)
            if 'api_used' in result:
                session['translation']['api'] = result['api_used']
            
            return redirect(url_for('result'))
        else:
            flash(result['message'])
            return redirect(url_for('index'))
    
    flash('Invalid file type. Only XML files are allowed.')
    return redirect(url_for('index'))

@app.route('/result')
def result():
    if 'translation' not in session:
        flash('No translation in progress. Please upload an XML file.')
        return redirect(url_for('index'))
    
    translation = session['translation']
    return render_template('result.html', translation=translation)

@app.route('/download')
def download():
    if 'translation' not in session or 'translated_path' not in session['translation']:
        flash('No translated file available')
        return redirect(url_for('index'))
    
    translated_path = session['translation']['translated_path']
    filename = session['translation']['filename']
    
    return send_file(translated_path, as_attachment=True, download_name=filename)

@app.route('/languages')
def languages():
    # Try each LibreTranslate instance until we find one that works
    for instance in LIBRETRANSLATE_INSTANCES:
        languages_url = f"{instance}/languages"
        try:
            response = requests.get(languages_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                libre_languages = response.json()
                language_pairs = []
                for lang in libre_languages:
                    language_pairs.append({
                        'code': lang['code'],
                        'name': lang['name']
                    })
                return {'languages': language_pairs}
        except Exception as e:
            app.logger.error(f"Error fetching LibreTranslate languages from {instance}: {str(e)}")
            # Try next instance
            continue
    
    # If all LibreTranslate instances fail, fall back to static list
    language_pairs = [
        {'code': 'en', 'name': 'English'},
        {'code': 'ru', 'name': 'Russian'},
        {'code': 'fr', 'name': 'French'},
        {'code': 'de', 'name': 'German'},
        {'code': 'es', 'name': 'Spanish'},
        {'code': 'it', 'name': 'Italian'},
        {'code': 'ja', 'name': 'Japanese'},
        {'code': 'ko', 'name': 'Korean'},
        {'code': 'zh', 'name': 'Chinese'},
        {'code': 'ar', 'name': 'Arabic'},
        {'code': 'hi', 'name': 'Hindi'},
        {'code': 'pt', 'name': 'Portuguese'},
        {'code': 'tr', 'name': 'Turkish'},
    ]
    return {'languages': language_pairs}

if __name__ == '__main__':
    app.run(debug=True) 