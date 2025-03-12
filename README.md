# XML Translator Web Application

This web application allows you to upload XML files, translate specific text fields to various languages, and download the translated XML files. It's specifically designed for translating mod files that contain fields like `strName` and `strDesc`.

## Features

- User-friendly web interface
- Upload and translate XML files with a few clicks
- Support for multiple languages (including Russian, English, and many more)
- Translation of specific fields within XML files
- Option to add custom fields to translate
- Multiple translation APIs:
  - **LibreTranslate** (default): Free, open-source, no rate limits
  - MyMemory: Free API with daily limits (5,000 characters/day)
  - Google Translate API: High quality (requires API key)
- Robust and reliable:
  - Multiple LibreTranslate servers for redundancy
  - Automatic retry and fallback mechanisms
  - Batch processing for large files
- Download translated XML files directly from the browser

## Screenshots

![XML Translator Homepage](screenshots/home.png)
![Translation Results](screenshots/results.png)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd xml-translator-web
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the Flask application:
   ```
   python app.py
   ```

4. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## About LibreTranslate

This application uses LibreTranslate as the default translation service. LibreTranslate is:

- Completely free and open-source
- Has no daily usage limits (unlike MyMemory)
- Requires no API key or registration
- Supports a wide range of languages including Russian

### Reliability Improvements

The application connects to multiple LibreTranslate public instances:
- libretranslate.de
- translate.argosopentech.com
- translate.terraprint.co
- lt.vern.cc

If one server fails or times out, the application automatically:
1. Tries alternative LibreTranslate servers
2. Falls back to MyMemory as a last resort
3. Processes large files in batches to prevent timeouts

This ensures your translations continue to work even if some servers are unavailable.

## Using Google Translate API (Optional)

For even better translation quality, you can use the Google Translate API:

1. Install the Google Cloud Translate package:
   ```
   pip install google-cloud-translate
   ```

2. Set up a Google Cloud project and enable the Cloud Translation API

3. Create a service account key and download the JSON file

4. Set the environment variable to your service account key file:
   - On Windows:
     ```
     set GOOGLE_APPLICATION_CREDENTIALS=path\to\your\credentials.json
     ```
   - On macOS/Linux:
     ```
     export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
     ```

## Usage

1. Open the web application in your browser
2. Upload an XML file (must have .xml extension and valid XML structure)
3. Select the source and target languages
4. Choose the translation API (LibreTranslate is default with no limits)
5. Select which fields to translate (default: strName and strDesc)
6. Click "Translate XML"
7. Once translation is complete, click "Download Translated XML"

## Command-Line Version

If you prefer a command-line interface, check out the following scripts included in this repository:

- `xml_translator.py`: Basic script using MyMemory API
- `google_xml_translator.py`: Script using Google Translate API
- `xml_translator_cli.py`: Command-line interface with various options

## Notes

- Machine translation may not be perfect. Consider reviewing the translations.
- LibreTranslate has no daily limits but may be slower than other APIs.
- If all LibreTranslate servers are unavailable, the app will use MyMemory as a fallback.
- MyMemory API has a limit of about 5,000 characters per day.
- XML structure is preserved, only the text content is translated.

## License

MIT 