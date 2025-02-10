import os
import xml.etree.ElementTree as ET
import json
import logging

class LegalDocumentExtractor:
    def __init__(self):
        self.namespaces = {
            'usc': 'http://xml.house.gov/schemas/uslm/1.0',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

    def extract_document_metadata(self, root: ET.Element) -> dict:
        metadata = {}
        meta = root.find('usc:meta', self.namespaces)
        if meta is not None:
            metadata['title'] = self.safe_find_text(meta, './/dc:title')
            metadata['type'] = self.safe_find_text(meta, './/dc:type')
            metadata['doc_number'] = self.safe_find_text(meta, './/usc:docNumber')

        title_element = root.find('.//usc:title', self.namespaces)
        if title_element is not None:
            num = self.safe_find_text(title_element, 'usc:num')
            heading = self.safe_find_text(title_element, 'usc:heading')
            metadata['full_title'] = f"{num} {heading}".strip()

        # Extract enactment date
        note_element = root.find('.//usc:note[@topic="enacting"]', self.namespaces)
        if note_element is not None:
            date_element = note_element.find('.//usc:date', self.namespaces)
            if date_element is not None:
                metadata['enactment_date'] = date_element.get('date')

        return metadata

    def safe_find_text(self, element, xpath, default="", log_warning=True):
        try:
            text_element = element.find(xpath, self.namespaces)
            if text_element is not None and text_element.text:
                return text_element.text.strip()
            else:
                return default
        except AttributeError:
            if log_warning:
                logging.warning(f"Could not find or extract text for xpath: {xpath}")
            return default

    def extract_chapters_and_sections(self, root: ET.Element) -> list:
        chapters_data = []

        chapters = root.findall('.//usc:chapter', self.namespaces)
        if chapters:
            for chapter in chapters:
                chapter_num = self.safe_find_text(chapter, 'usc:num', default='Unknown', log_warning=False)
                chapter_heading = self.safe_find_text(chapter, 'usc:heading', default='Unknown', log_warning=False)

                sections_data = []
                for section in chapter.findall('.//usc:section', self.namespaces):
                    section_num = self.safe_find_text(section, 'usc:num', default='Unknown', log_warning=False)
                    section_heading = self.safe_find_text(section, 'usc:heading', default='Unknown', log_warning=False)
                    section_text = self.extract_section_text(section)

                    sections_data.append({
                        'section_number': section_num,
                        'section_title': section_heading,
                        'section_text': section_text
                    })

                chapters_data.append({
                    'chapter_number': chapter_num,
                    'chapter_title': chapter_heading,
                    'sections': sections_data
                })
        else:
            # No chapters found, process sections at the root level
            sections_data = []
            for section in root.findall('.//usc:section', self.namespaces):
                section_num = self.safe_find_text(section, 'usc:num', default='Unknown', log_warning=False)
                section_heading = self.safe_find_text(section, 'usc:heading', default='Unknown', log_warning=False)
                section_text = self.extract_section_text(section)

                sections_data.append({
                    'section_number': section_num,
                    'section_title': section_heading,
                    'section_text': section_text
                })

            chapters_data.append({
                'chapter_number': 'Unknown',
                'chapter_title': 'Unknown',
                'sections': sections_data
            })

        return chapters_data

    def extract_section_text(self, section: ET.Element) -> str:
        text_content = ET.tostring(section, encoding='unicode', method='text')
        return text_content.strip()

    def process_legal_document(self, file_path: str):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            document_metadata = self.extract_document_metadata(root)
            chapters_data = self.extract_chapters_and_sections(root)

            # Combine metadata and chapters data
            document_data = {
                'metadata': document_metadata,
                'chapters': chapters_data
            }

            # Save to JSON file
            output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.json'
            output_dir = 'output_json'
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Processed and saved data to {output_path}")

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    extractor = LegalDocumentExtractor()

    xml_folder = "constitution/xml"  # Update this path to where your XML files are located
    for filename in os.listdir(xml_folder):
        if filename.endswith(".xml"):
            file_path = os.path.join(xml_folder, filename)
            logging.info(f"Processing file: {file_path}")
            extractor.process_legal_document(file_path)

    logging.info("Processing completed.")

if __name__ == "__main__":
    main()