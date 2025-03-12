#!/usr/bin/env python3
"""
XML Translator for Mods

This script parses XML files in the specified directory, translates specific text fields
to the target language, and updates the XML files with the translated content.
"""

import os
import sys
import xml.etree.ElementTree as ET
import argparse
import time
import requests
from tqdm import tqdm

try:
    from google.cloud import translate_v2 as google_translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False

# Default configuration
DEFAULT_SRC_LANG = "en"
DEFAULT_TARGET_LANG = "ru"
DEFAULT_FIELDS_TO_TRANSLATE = ["strName", "strDesc"]
DEFAULT_XML_FILES_PATH = "Mods"
DEFAULT_API = "mymemory"  # Options: mymemory, google
DEFAULT_MYMEMORY_API_URL = "https://api.mymemory.translated.net/get"

def find_all_xml_files(root_dir, include_pattern=None, exclude_pattern=None):
    """Find all XML files in the given directory and its subdirectories."""
    xml_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.endswith('.xml'):
                continue
                
            file_path = os.path.join(dirpath, filename)
            
            # Apply include/exclude filters
            if include_pattern and include_pattern not in file_path:
                continue
            if exclude_pattern and exclude_pattern in file_path:
                continue
                
            xml_files.append(file_path)
    return xml_files

def translate_with_mymemory(text, src_lang, target_lang, api_url=DEFAULT_MYMEMORY_API_URL):
    """Translate text using MyMemory Translation API."""
    if not text or text.strip() == "":
        return text
    
    params = {
        'q': text,
        'langpair': f'{src_lang}|{target_lang}'
    }
    
    try:
        response = requests.get(api_url, params=params)
        response_json = response.json()
        
        if response.status_code == 200 and response_json['responseStatus'] == 200:
            translated_text = response_json['responseData']['translatedText']
            return translated_text
        else:
            print(f"Translation error: {response_json.get('responseDetails', 'Unknown error')}")
            return text
    except Exception as e:
        print(f"Error during translation: {str(e)}")
        return text

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
        print(f"Error during Google translation: {str(e)}")
        return text

def translate_text(text, src_lang, target_lang, api="mymemory"):
    """Translate text using the specified API."""
    if not text or text.strip() == "":
        return text
    
    # Replace XML entities to prevent translation issues
    text = text.replace("&lt;", "<LESSTHAN>").replace("&gt;", "<GREATERTHAN>")
    
    if api == "google" and GOOGLE_TRANSLATE_AVAILABLE:
        translated_text = translate_with_google(text, src_lang, target_lang)
    else:
        translated_text = translate_with_mymemory(text, src_lang, target_lang)
    
    # Restore XML entities
    translated_text = translated_text.replace("<LESSTHAN>", "&lt;").replace("<GREATERTHAN>", "&gt;")
    return translated_text

def translate_xml_file(xml_file_path, src_lang, target_lang, fields_to_translate, api, backup_suffix, dry_run, delay):
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
                if column.get("name") in fields_to_translate and column.text:
                    elements_to_translate.append(column)
        
        if not elements_to_translate:
            print(f"No text to translate in {xml_file_path}")
            return
        
        print(f"Found {len(elements_to_translate)} elements to translate")
        
        # Create backup of original file if not a dry run
        if not dry_run:
            backup_path = f"{xml_file_path}.{backup_suffix}"
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(xml_file_path, backup_path)
                print(f"Created backup at {backup_path}")
        
        # Translate elements
        for column in tqdm(elements_to_translate, desc="Translating"):
            if column.text:
                original_text = column.text
                translated_text = translate_text(original_text, src_lang, target_lang, api)
                
                if dry_run:
                    print(f"Would translate: {original_text} -> {translated_text}")
                else:
                    column.text = translated_text
                
                # Avoid rate limiting
                time.sleep(delay)
        
        # Save translated XML if not a dry run
        if not dry_run:
            tree.write(xml_file_path, encoding="utf-8", xml_declaration=True)
            print(f"Saved translated XML to {xml_file_path}")
        
    except Exception as e:
        print(f"Error processing {xml_file_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Translate XML files for mods")
    parser.add_argument("--path", default=DEFAULT_XML_FILES_PATH, help="Path to directory containing XML files")
    parser.add_argument("--src-lang", default=DEFAULT_SRC_LANG, help="Source language code")
    parser.add_argument("--target-lang", default=DEFAULT_TARGET_LANG, help="Target language code")
    parser.add_argument("--fields", nargs="+", default=DEFAULT_FIELDS_TO_TRANSLATE, help="XML fields to translate")
    parser.add_argument("--api", choices=["mymemory", "google"], default=DEFAULT_API, help="Translation API to use")
    parser.add_argument("--include", help="Only process files that include this pattern")
    parser.add_argument("--exclude", help="Skip files that include this pattern")
    parser.add_argument("--backup-suffix", default="backup", help="Suffix for backup files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between translation requests in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be translated without making changes")
    parser.add_argument("--file", help="Process a specific XML file instead of searching for files")
    
    args = parser.parse_args()
    
    # Check if Google Translate is requested but not available
    if args.api == "google" and not GOOGLE_TRANSLATE_AVAILABLE:
        print("Error: Google Translate API requested but 'google-cloud-translate' package is not installed.")
        print("Install it with: pip install google-cloud-translate")
        sys.exit(1)
    
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set when using Google Translate
    if args.api == "google" and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        print("Warning: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your Google Cloud service account key file.")
        print("Example: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json")
        proceed = input("Do you want to proceed anyway? (y/n): ")
        if proceed.lower() != 'y':
            sys.exit(1)
    
    # Find XML files
    if args.file:
        if os.path.isfile(args.file) and args.file.endswith('.xml'):
            xml_files = [args.file]
        else:
            print(f"Error: {args.file} is not a valid XML file")
            sys.exit(1)
    else:
        xml_files = find_all_xml_files(args.path, args.include, args.exclude)
    
    print(f"Found {len(xml_files)} XML files to process")
    
    # Process each XML file
    for xml_file in xml_files:
        translate_xml_file(
            xml_file, 
            args.src_lang, 
            args.target_lang, 
            args.fields, 
            args.api, 
            args.backup_suffix, 
            args.dry_run,
            args.delay
        )
        print(f"Finished processing {xml_file}")
        print("-" * 50)

if __name__ == "__main__":
    main() 