import os
from xml.dom import minidom
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import json
import logging
from typing import List, Dict, Any
from xml.etree.ElementTree import Element, tostring
import uuid
import re
import math

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

class LegalDocumentProcessor:
    def __init__(self):
        self.processed_files = set()
        self.namespaces = {
            'usc': 'http://xml.house.gov/schemas/uslm/1.0',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }
        self.batch_requests = []
        self.request_mapping = {}
        self.max_chunk_size = 100000  # Maximum number of characters per chunk
        self.max_batch_size = 170 * 1024 * 1024  # 200 MB in bytes
        self.current_batch_size = 0
        self.current_batch_index = 0

    def _extract_document_metadata(self, root: ET.Element) -> Dict[str, Any]:
        metadata = {}
        meta = root.find('usc:meta', self.namespaces)
        if meta is not None:
            metadata['title'] = self.safe_find_text(meta, './/dc:title')
            metadata['type'] = self.safe_find_text(meta, './/dc:type')
            metadata['doc_number'] = self.safe_find_text(meta, './/usc:docNumber')
        
        title_element = root.find('.//usc:title', self.namespaces)
        if title_element is not None:
            num = self.safe_find_text(title_element, './/usc:num')
            heading = self.safe_find_text(title_element, './/usc:heading')
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
            return element.find(xpath, self.namespaces).text.strip()
        except AttributeError:
            if log_warning:
                logging.warning(f"Could not find or extract text for xpath: {xpath}")
            return default

    def clean_xml(self, root: Element) -> Element:
        # Update the namespace map
        self.namespaces = {
            'usc': 'http://xml.house.gov/schemas/uslm/1.0',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

        # Find the main content
        main = root.find('.//usc:main', self.namespaces)
        if main is None:
            logging.warning("No main content found in the document.")
            return None

        def clean_element(element):
            # Create a new element with the same tag, but without the namespace
            new_element = Element(element.tag.split('}')[-1])
            
            # Copy text and tail
            new_element.text = element.text
            new_element.tail = element.tail
            
            # Copy attributes, excluding unnecessary ones
            for attr, value in element.attrib.items():
                if attr not in ['class', 'style', 'id', 'identifier', 'href']:
                    new_element.set(attr, value)
            
            # Recursively clean child elements
            for child in element:
                new_child = clean_element(child)
                if new_child is not None:
                    new_element.append(new_child)
            
            return new_element

        # Clean all elements in the main content
        cleaned_root = Element('root')
        for element in main:
            cleaned_element = clean_element(element)
            cleaned_root.append(cleaned_element)

        return cleaned_root

    def prettify(self, elem):
        """Return a pretty-printed XML string for the Element."""
        rough_string = tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def chunk_by_chapters(self, root: ET.Element) -> List[Dict[str, Any]]:
        chunks = []
        for chapter in root.findall('.//chapter'):
            chapter_num = chapter.find('num')
            chapter_number = chapter_num.text if chapter_num is not None else "Unknown"
            
            chapter_heading = chapter.find('heading')
            chapter_title = chapter_heading.text if chapter_heading is not None else "Unknown"
            
            sections = chapter.findall('.//section')
            for i in range(0, len(sections), 5):  # Group sections in batches of 5
                section_batch = sections[i:i+5]
                section_data = []
                for section in section_batch:
                    section_num = section.find('num')
                    section_heading = section.find('heading')
                    section_data.append({
                        'number': section_num.text if section_num is not None else "Unknown",
                        'title': section_heading.text if section_heading is not None else "Unknown",
                        'content': ET.tostring(section, encoding='unicode', method='xml')
                    })
                
                chunks.append({
                    'chapter_number': chapter_number,
                    'chapter_title': chapter_title,
                    'sections': section_data
                })
        
        # If no chapters were found, include the entire document as a single chunk
        if not chunks:
            chunks.append({
                'chapter_number': "Unknown",
                'chapter_title': "Unknown",
                'sections': [{
                    'number': "Unknown",
                    'title': "Unknown",
                    'content': ET.tostring(root, encoding='unicode', method='xml')
                }]
            })
        
        return chunks

    def split_large_chunk(self, chunk: str) -> List[str]:
        words = chunk.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            if current_size + len(word) + 1 > self.max_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1  # +1 for the space

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def process_legal_document(self, file_path: str):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            document_metadata = self._extract_document_metadata(root)
            cleaned_root = self.clean_xml(root)
            
            if cleaned_root is None:
                logging.warning(f"No content found after cleaning for {file_path}")
                return None

            chapters = self.chunk_by_chapters(cleaned_root)

            logging.info(f"Processing {len(chapters)} chunks for {file_path}")

            for chunk_index, chunk in enumerate(chapters):
                request_id = str(uuid.uuid4())
                self.create_batch_request(chunk, request_id)
                self.request_mapping[request_id] = {
                    "file_path": file_path,
                    "chunk_index": chunk_index,
                    "chapter_number": chunk['chapter_number'],
                    "chapter_title": chunk['chapter_title'],
                    "sections": [{"number": s['number'], "title": s['title']} for s in chunk['sections']],
                    "metadata": document_metadata
                }

            self.processed_files.add(file_path)

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")

    def create_batch_request(self, chunk: Dict[str, Any], request_id: str):
        prompt = f"""
        Please process the provided chunk of a legal document and extract structured data from it based on the desired JSON structure.
        Chapter Number: {chunk['chapter_number']}
        Chapter Title: {chunk['chapter_title']}
        Sections:
        {json.dumps(chunk['sections'], indent=2)}
        """

        system_prompt = """
        You will be provided with a piece of a legal document. Your task is to parse structured data from it, ensuring accuracy, consistency, and clarity as it would be used for a knowledge graph database. 

        Here is the desired JSON structure:
        {
          "chapter_number": "CHAPTER XXX",
          "chapter_title": "Chapter Title",
          "sections": [
            {
              "section_number": "XXXXX",
              "section_title": "Section Title",
              "scope": ["entity1", "entity2"],
              "definitions": ["term1", "term2"],
              "substantive_provisions": ["provision1", "provision2"],
              "conditions": ["condition1", "condition2"],
              "consequences": ["consequence1", "consequence2"]
            }
          ]
        }

        Please process the provided chunk and extract structured data from it. 
        * Ensure that all sections have numbers and titles.
        * Maintain the YYYY-MM-DD format for the enactment date if present.

        Return the complete JSON object as your output, including all nested dictionaries and arrays, without any additional text or formatting.
        """

        request = {
            "custom_id": request_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 3000
            }
        }

        request_size = len(json.dumps(request))
        if self.current_batch_size + request_size > self.max_batch_size:
            self.save_current_batch()
            self.current_batch_index += 1
            self.current_batch_size = 0
            self.batch_requests = []

        self.batch_requests.append(request)
        self.current_batch_size += request_size

    def save_current_batch(self):
        if not self.batch_requests:
            return

        output_path = f"batch_requests_{self.current_batch_index}.jsonl"
        with open(output_path, 'w') as f:
            for request in self.batch_requests:
                json.dump(request, f)
                f.write('\n')
        logging.info(f"Batch file saved to {output_path}")

    def save_batch_file(self, output_path: str):
        # This method is no longer needed, but we'll keep it for backwards compatibility
        self.save_current_batch()

    def save_request_mapping(self, output_path: str):
        with open(output_path, 'w') as f:
            json.dump(self.request_mapping, f, indent=2)
        logging.info(f"Request mapping saved to {output_path}")

async def main():
    load_dotenv()
    processor = LegalDocumentProcessor()
    
    xml_folder = "constitution/xml"
    for filename in os.listdir(xml_folder):
        if filename.endswith(".xml"):
            file_path = os.path.join(xml_folder, filename)
            logging.info(f"Processing file: {file_path}")
            processor.process_legal_document(file_path)

    # Save any remaining batch requests
    processor.save_current_batch()
    processor.save_request_mapping("request_mapping.json")

    logging.info("Processing completed.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())