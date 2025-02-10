import os
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import json
import asyncio
from api_wrapper import get_api
from tqdm import tqdm
import re
import logging
from typing import List, Dict, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

class LegalDocumentProcessor:
    def __init__(self):
        self.api = None
        self.processed_files = set()
        self.namespaces = {
            'usc': 'http://xml.house.gov/schemas/uslm/1.0',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

    @classmethod
    async def create(cls, api_name, model_name):
        self = cls()
        self.api = await get_api(api_name, model_name)
        return self

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

    def chunk_by_chapters(self, root: ET.Element) -> List[str]:
        chunks = []
        for chapter in root.findall('.//chapter'):
            chapter_text = ET.tostring(chapter, encoding='unicode', method='xml')
            chunks.append(chapter_text)
        
        # If no chapters were found, include the entire document as a single chunk
        if not chunks:
            chunks.append(ET.tostring(root, encoding='unicode', method='xml'))
        
        return chunks

    async def process_legal_document(self, file_path: str):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            document_metadata = self._extract_document_metadata(root)
            cleaned_root = self.clean_xml(root)
            
            if cleaned_root is None:
                logging.warning(f"No content found after cleaning for {file_path}")
                return None

            chunks = self.chunk_by_chapters(cleaned_root)

            logging.info(f"Processing {len(chunks)} chapters for {file_path}")

            processed_chunks = []
            for i, chunk in enumerate(tqdm(chunks, desc="Processing chapters")):
                logging.info(f"Processing chapter {i+1}/{len(chunks)}")
                processed_chunk = await self._process_chunk(chunk)
                processed_chunks.append(processed_chunk)

            merged_data = self._merge_processed_chunks(processed_chunks)

            final_document_data = {
                **document_metadata,
                "file_path": file_path,
                "extracted_data": merged_data
            }

            json_file_path = file_path.replace('.xml', '.json')
            with open(json_file_path, 'w') as f:
                json.dump(final_document_data, f, indent=2)

            logging.info(f"Created JSON file: {json_file_path}")
            self.processed_files.add(file_path)

            return final_document_data

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")
            return None

    async def _process_chunk(self, chunk: str) -> Dict[str, Any]:
        properties = await self._extract_properties_with_llm(chunk)
        return properties

    async def _extract_properties_with_llm(self, chunk: str) -> Dict[str, Any]:
        prompt = f"""
        Given the following chunk of a legal document, please extract the following properties:
        1. scope (entities or individuals to whom this chunk applies)
        2. definitions (key terms and their meanings used in this chunk)
        3. substantive_provisions (main rules or obligations set by this chunk)
        4. conditions (circumstances under which this chunk applies)
        5. consequences (penalties or effects of non-compliance with this chunk)

        Please return the results in JSON format, strictly adhering to the provided template.

        Chunk content:
        {chunk} 
        """

        system_prompt = "You are a helpful assistant that extracts specific information from legal documents. Always respond with valid JSON that matches the provided template exactly."
        
        response = await self._generate_text(prompt, system_prompt, format="json")
        
        if not response:
            logging.warning("Received empty response from LLM")
            return {}
        
        try:
            extracted_json = self._extract_json_from_response(response)
            if not extracted_json:
                logging.warning("Failed to extract valid JSON from LLM response")
                return {}
            
            return extracted_json
        except Exception as e:
            logging.error(f"Error processing LLM response: {e}")
            return {}

    def _merge_processed_chunks(self, processed_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        merged_data = {
            "scope": set(),
            "definitions": [],
            "substantive_provisions": [],
            "conditions": [],
            "consequences": []
        }

        for chunk_data in processed_chunks:
            merged_data["scope"].add(chunk_data.get("scope", ""))
            merged_data["definitions"].extend(chunk_data.get("definitions", []))
            merged_data["substantive_provisions"].extend(chunk_data.get("substantive_provisions", []))
            merged_data["conditions"].extend(chunk_data.get("conditions", []))
            merged_data["consequences"].extend(chunk_data.get("consequences", []))

        # Clean up and format the merged data
        merged_data["scope"] = self._clean_and_format_list(list(filter(None, merged_data["scope"])), capitalize_first=True)
        merged_data["definitions"] = self._clean_and_format_list(merged_data["definitions"], title_case=True)
        merged_data["substantive_provisions"] = self._clean_and_format_list(merged_data["substantive_provisions"], capitalize_first=True)
        merged_data["conditions"] = self._clean_and_format_list(merged_data["conditions"], capitalize_first=True)
        merged_data["consequences"] = self._clean_and_format_list(merged_data["consequences"], capitalize_first=True)

        return merged_data

    def _clean_and_format_list(self, items: List[str], title_case: bool = False, capitalize_first: bool = False) -> List[str]:
        # Remove duplicates and single-character entries
        cleaned_items = list({item for item in items if len(item.strip()) > 1})
        
        # Format items
        formatted_items = []
        for item in cleaned_items:
            if title_case:
                formatted_item = item.title()
            elif capitalize_first:
                formatted_item = item.capitalize()
            else:
                formatted_item = item
            formatted_items.append(formatted_item)
        
        return formatted_items

    async def _generate_text(self, prompt: str, system_prompt: str, format: str = None) -> str:
        response = ""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logging.info(f"Sending prompt to LLM (attempt {attempt + 1}/{max_retries})")
                async for text_chunk in self.api.generate_text(prompt, system_prompt, format=format):
                    response += text_chunk
    
                if response:
                    logging.info(f"Received response from LLM (length: {len(response)})")
                    logging.info(f"Raw LLM response: {response[:500]}...")  # Only log the first 500 characters
                    return response
                else:
                    logging.warning(f"Received empty response from API (attempt {attempt + 1}/{max_retries})")
            except Exception as e:
                logging.error(f"Error generating text (attempt {attempt + 1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait a bit before retrying
    
        logging.error("Failed to generate text after multiple attempts")
        return ""

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        logging.info("Extracting JSON from response")
        
        try:
            # Try to parse the entire response as JSON first
            return json.loads(response)
        except json.JSONDecodeError:
            # If that fails, try to find JSON between triple backticks
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # If that fails, try to find anything that looks like JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass
        
        logging.warning("Failed to extract valid JSON from LLM response")
        return {}

async def main():
    load_dotenv()
    processor = await LegalDocumentProcessor.create("openai", "gpt-4o-mini")
    try:
        # Process a single file for debugging
        file_path = "constitution/xml/usc09.xml"  # Change this to the file you want to process
        await processor.process_legal_document(file_path)
    except FileNotFoundError:
        logging.error(f"The specified file does not exist: {file_path}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Processing completed.")
        await processor.api.close()

if __name__ == "__main__":
    asyncio.run(main())