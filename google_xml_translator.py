import os
import xml.etree.ElementTree as ET
import time
from tqdm import tqdm
from google.cloud import translate_v2 as translate

# Configuration
SRC_LANG = "en"
TARGET_LANG = "ru"
FIELDS_TO_TRANSLATE = ["strName", "strDesc"]  # Fields that contain text to translate
XML_FILES_PATH = "Mods"  # Path to the directory containing XML files

def find_all_xml_files(root_dir):
    """Find all XML files in the given directory and its subdirectories."""
    xml_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.xml'):
                xml_files.append(os.path.join(dirpath, filename))
    return xml_files

def translate_text(text, src_lang=SRC_LANG, target_lang=TARGET_LANG):
    """Translate text using Google Translate API."""
    if not text or text.strip() == "":
        return text
    
    # Replace XML entities to prevent translation issues
    text = text.replace("&lt;", "<LESSTHAN>").replace("&gt;", "<GREATERTHAN>")
    
    try:
        translate_client = translate.Client()
        result = translate_client.translate(
            text, 
            target_language=target_lang,
            source_language=src_lang
        )
        
        translated_text = result['translatedText']
        # Restore XML entities
        translated_text = translated_text.replace("<LESSTHAN>", "&lt;").replace("<GREATERTHAN>", "&gt;")
        return translated_text
    except Exception as e:
        print(f"Error during translation: {str(e)}")
        return text

def translate_xml_file(xml_file_path):
    """Parse XML file, translate specified fields, and save the translated XML."""
    print(f"Processing {xml_file_path}")
    
    try:
        # Parse XML
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Count elements that need translation
        elements_to_translate = []
        for table in root.findall(".//table"):
            for column in table.findall("column"):
                if column.get("name") in FIELDS_TO_TRANSLATE and column.text:
                    elements_to_translate.append(column)
        
        if not elements_to_translate:
            print(f"No text to translate in {xml_file_path}")
            return
        
        print(f"Found {len(elements_to_translate)} elements to translate")
        
        # Translate elements
        for column in tqdm(elements_to_translate, desc="Translating"):
            if column.text:
                original_text = column.text
                translated_text = translate_text(original_text)
                column.text = translated_text
                # Avoid rate limiting
                time.sleep(0.1)
        
        # Create backup of original file
        backup_path = xml_file_path + ".google.backup"
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(xml_file_path, backup_path)
            print(f"Created backup at {backup_path}")
        
        # Save translated XML
        tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)
        print(f"Saved translated XML to {xml_file_path}")
        
    except Exception as e:
        print(f"Error processing {xml_file_path}: {str(e)}")

def main():
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set
    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your Google Cloud service account key file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json")
        proceed = input("Do you want to proceed anyway? (y/n): ")
        if proceed.lower() != 'y':
            return
    
    # Find all XML files
    xml_files = find_all_xml_files(XML_FILES_PATH)
    print(f"Found {len(xml_files)} XML files")
    
    # Process each XML file
    for xml_file in xml_files:
        translate_xml_file(xml_file)
        print(f"Finished processing {xml_file}")
        print("-" * 50)

if __name__ == "__main__":
    main() 