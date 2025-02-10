import os
import json
import xml.etree.ElementTree as ET
import logging
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ChapterTitleUpdater:
    def __init__(self):
        self.namespaces = {
            'usc': 'http://xml.house.gov/schemas/uslm/1.0',
        }

    def normalize_chapter_number(self, chapter_number):
        # Extract only the numeric part
        normalized = re.sub(r'\D', '', chapter_number)
        logging.debug(f"Normalized chapter number: '{chapter_number}' to '{normalized}'")
        return normalized

    def extract_chapter_titles(self, xml_path):
        logging.debug(f"Extracting chapter titles from {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        chapter_titles = {}

        for chapter in root.findall('.//usc:chapter', self.namespaces):
            num = chapter.find('usc:num', self.namespaces)
            heading = chapter.find('usc:heading', self.namespaces)
            if num is not None and heading is not None:
                chapter_number = num.get('value', '')
                chapter_titles[chapter_number] = heading.text.strip()
                logging.debug(f"Found chapter {chapter_number}: {heading.text.strip()}")

        logging.debug(f"Extracted chapter titles: {chapter_titles}")
        return chapter_titles

    def update_json_file(self, json_path, xml_path):
        logging.debug(f"Updating JSON file: {json_path}")
        with open(json_path, 'r') as f:
            data = json.load(f)

        chapter_titles = self.extract_chapter_titles(xml_path)

        updated = False
        if 'chapters' in data:
            for chapter in data['chapters']:
                if 'chapter_number' in chapter:
                    chapter_number = self.normalize_chapter_number(chapter['chapter_number'])
                    if chapter_number in chapter_titles:
                        chapter['chapter_title'] = chapter_titles[chapter_number]
                        updated = True
                        logging.debug(f"Updated chapter {chapter_number} with title: {chapter_titles[chapter_number]}")
                    else:
                        logging.warning(f"No title found for chapter {chapter_number} in XML")

        if updated:
            with open(json_path, 'w') as f:
                json.dump(data, f, indent=2)
            logging.info(f"Updated {json_path} with chapter titles")
        else:
            logging.info(f"No updates needed for {json_path}")

    def process_files(self, json_folder, xml_folder):
        for filename in os.listdir(json_folder):
            if filename.endswith('.json'):
                json_path = os.path.join(json_folder, filename)
                xml_filename = filename.replace('.json', '.xml')
                xml_path = os.path.join(xml_folder, xml_filename)

                if os.path.exists(xml_path):
                    logging.info(f"Processing {filename}")
                    self.update_json_file(json_path, xml_path)
                else:
                    logging.warning(f"Corresponding XML file not found for {filename}")

def main():
    json_folder = "constitution/json"
    xml_folder = "constitution/xml"
    
    updater = ChapterTitleUpdater()
    updater.process_files(json_folder, xml_folder)

    logging.info("Processing completed.")

if __name__ == "__main__":
    main()