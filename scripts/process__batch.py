import os
import json
import logging
import uuid
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class JSONProcessor:
    def __init__(self):
        self.batch_requests = []
        self.request_mapping = {}
        self.max_batch_size = 150 * 1024 * 1024  # 150 MB in bytes
        self.current_batch_size = 0
        self.current_batch_index = 0
        self.max_chunk_size = 100000  # Maximum number of characters per chunk

    def process_json_files(self, file_path1: str, file_path2: str):
        try:
            with open(file_path1, 'r') as f1, open(file_path2, 'r') as f2:
                json_data1 = json.load(f1)
                json_data2 = json.load(f2)
            
            if not isinstance(json_data1, dict) or not isinstance(json_data2, dict):
                raise ValueError("JSON data is not in the expected dictionary format")
            
            # Ensure 'chapters' key exists in both JSONs
            if 'chapters' not in json_data1:
                json_data1['chapters'] = []
            if 'chapters' not in json_data2:
                json_data2['chapters'] = []
            
            merged_data = self.merge_json_data(json_data1, json_data2)
            
            # Chunk the merged data
            chunks = self.chunk_json_data(merged_data)
            
            for chunk_index, chunk in enumerate(chunks):
                request_id = str(uuid.uuid4())
                self.create_batch_request(chunk, request_id)
                self.request_mapping[request_id] = {
                    "file_path1": file_path1,
                    "file_path2": file_path2,
                    "chunk_index": chunk_index
                }

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON in files {file_path1} or {file_path2}: {str(e)}")
        except ValueError as e:
            logging.error(f"Error processing files {file_path1} and {file_path2}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error processing files {file_path1} and {file_path2}: {str(e)}")

    def merge_json_data(self, json1: Dict[str, Any], json2: Dict[str, Any]) -> Dict[str, Any]:
        merged = json1.copy()
        
        # Merge top-level fields
        for key in ['title', 'type', 'doc_number', 'full_title', 'enactment_date']:
            if key in json2 and json2[key] is not None:
                merged[key] = json2[key]
        
        if 'chapters' in merged and 'chapters' in json2:
            for i, chapter1 in enumerate(merged['chapters']):
                if i < len(json2['chapters']):
                    chapter2 = json2['chapters'][i]
                    
                    # Merge chapter title
                    if 'chapter_title' in chapter2 and chapter2['chapter_title']:
                        chapter1['chapter_title'] = chapter2['chapter_title']
                    
                    # Merge entities into scope
                    if 'entities' in chapter2:
                        chapter1['scope'] = chapter1.get('scope', []) + self.extract_entities(chapter2['entities'])
                    
                    # Merge concepts into definitions
                    if 'concepts' in chapter2:
                        chapter1['definitions'] = chapter1.get('definitions', []) + self.extract_concepts(chapter2['concepts'])
                    
                    # Merge substantive_provisions
                    if 'substantive_provisions' in chapter2:
                        chapter1['substantive_provisions'] = chapter1.get('substantive_provisions', []) + self.extract_provisions(chapter2['substantive_provisions'])
                    
                    # Merge conditions
                    if 'conditions' in chapter2:
                        chapter1['conditions'] = chapter1.get('conditions', []) + self.extract_provisions(chapter2['conditions'])
                    
                    # Merge consequences
                    if 'consequences' in chapter2:
                        chapter1['consequences'] = chapter1.get('consequences', []) + self.extract_provisions(chapter2['consequences'])
        
        return merged

    def extract_entities(self, entities):
        if not entities:
            return []
        if isinstance(entities, list):
            return [self.extract_entity(e) for e in entities]
        elif isinstance(entities, dict):
            return [self.extract_entity(entities)]
        else:
            return [str(entities)]

    def extract_entity(self, entity):
        if isinstance(entity, dict):
            if 'description' in entity:
                return entity['description']
            elif 'entity' in entity and 'description' in entity:
                return f"{entity['entity']}: {entity['description']}"
            else:
                return str(entity)
        else:
            return str(entity)

    def extract_concepts(self, concepts):
        if not concepts:
            return []
        if isinstance(concepts, list):
            return [self.extract_concept(c) for c in concepts]
        elif isinstance(concepts, dict):
            return [self.extract_concept(concepts)]
        else:
            return [str(concepts)]

    def extract_concept(self, concept):
        if isinstance(concept, dict):
            if 'term' in concept and 'definition' in concept:
                return f"{concept['term']}: {concept['definition']}"
            elif 'definition' in concept:
                return concept['definition']
            else:
                return str(concept)
        else:
            return str(concept)

    def extract_provisions(self, provisions):
        if not provisions:
            return []
        if isinstance(provisions, list):
            return [self.extract_provision(p) for p in provisions]
        elif isinstance(provisions, dict):
            return [self.extract_provision(provisions)]
        else:
            return [str(provisions)]

    def extract_provision(self, provision):
        if isinstance(provision, dict):
            if 'provisions' in provision:
                return provision['provisions']
            elif 'heading' in provision and 'provisions' in provision:
                return f"{provision['heading']}: {'; '.join(provision['provisions'])}"
            else:
                return str(provision)
        else:
            return str(provision)

    def chunk_json_data(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        chunks = []
        current_chunk = {}
        current_size = 0

        for key, value in json_data.items():
            if key == 'chapters':
                for chapter in value:
                    chapter_str = json.dumps(chapter)
                    if current_size + len(chapter_str) > self.max_chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = {'chapters': [chapter]}
                        current_size = len(chapter_str)
                    else:
                        if 'chapters' not in current_chunk:
                            current_chunk['chapters'] = []
                        current_chunk['chapters'].append(chapter)
                        current_size += len(chapter_str)
            else:
                current_chunk[key] = value
                current_size += len(json.dumps({key: value}))

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def create_batch_request(self, json_data: Dict[str, Any], request_id: str):
        # Add minimal metadata to the json_data
        document_id = f"{json_data['title']}_{json_data['doc_number']}"
        chapter_number = json_data['chapters'][0]['chapter_number']
        chunk_index = self.request_mapping[request_id]['chunk_index']

        json_data['__metadata__'] = {
            'document_id': document_id,
            'chapter_number': chapter_number,
            'chunk_index': chunk_index
        }

        system_prompt = """
        You are provided with JSON data representing a chunk of a legal document chapter. Your task is to process this data and return only the following fields:
        - scope
        - definitions
        - substantive_provisions
        - conditions
        - consequences

        Ensure that all fields are lists of strings. Include the provided metadata in your response.

        Return the processed data as a JSON object.
        """

        user_prompt = f"Please process the following JSON data:\n\n{json.dumps(json_data, indent=2)}"

        request = {
            "custom_id": request_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 4000
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

        output_path = f"j_batch_requests_{self.current_batch_index}.jsonl"
        with open(output_path, 'w') as f:
            for request in self.batch_requests:
                json.dump(request, f)
                f.write('\n')
        logging.info(f"Batch file saved to {output_path}")

    def save_request_mapping(self, output_path: str):
        # Include full document and chapter metadata in the request mapping
        for request_id, mapping in self.request_mapping.items():
            file_path1 = mapping['file_path1']
            with open(file_path1, 'r') as f:
                json_data = json.load(f)
            
            mapping['document_metadata'] = {
                'title': json_data['title'],
                'type': json_data['type'],
                'doc_number': json_data['doc_number'],
                'full_title': json_data['full_title'],
                'enactment_date': json_data['enactment_date']
            }
            
            chapter_index = mapping['chunk_index'] // len(json_data['chapters'])
            mapping['chapter_metadata'] = {
                'chapter_number': json_data['chapters'][chapter_index]['chapter_number'],
                'chapter_title': json_data['chapters'][chapter_index]['chapter_title']
            }

        with open(output_path, 'w') as f:
            json.dump(self.request_mapping, f, indent=2)
        logging.info(f"Request mapping saved to {output_path}")

def reconstruct_documents(request_mapping: Dict[str, Any], llm_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    documents = {}

    for response in llm_responses:
        metadata = response['__metadata__']
        doc_id = metadata['document_id']
        chapter_number = metadata['chapter_number']

        if doc_id not in documents:
            doc_metadata = request_mapping[response['custom_id']]['document_metadata']
            documents[doc_id] = {
                'title': doc_metadata['title'],
                'type': doc_metadata['type'],
                'doc_number': doc_metadata['doc_number'],
                'full_title': doc_metadata['full_title'],
                'enactment_date': doc_metadata['enactment_date'],
                'chapters': {}
            }

        if chapter_number not in documents[doc_id]['chapters']:
            chapter_metadata = request_mapping[response['custom_id']]['chapter_metadata']
            documents[doc_id]['chapters'][chapter_number] = {
                'chapter_number': chapter_metadata['chapter_number'],
                'chapter_title': chapter_metadata['chapter_title'],
                'scope': [],
                'definitions': [],
                'substantive_provisions': [],
                'conditions': [],
                'consequences': []
            }

        chapter = documents[doc_id]['chapters'][chapter_number]
        for field in ['scope', 'definitions', 'substantive_provisions', 'conditions', 'consequences']:
            chapter[field].extend(response[field])

    # Convert chapters from dict to list and sort by chapter number
    for doc in documents.values():
        doc['chapters'] = sorted(doc['chapters'].values(), key=lambda x: x['chapter_number'])

    return documents

def main():
    processor = JSONProcessor()
    
    json_folder1 = "constitution/json"
    json_folder2 = "constitution/json2"
    
    for filename in os.listdir(json_folder1):
        if filename.endswith(".json"):
            file_path1 = os.path.join(json_folder1, filename)
            file_path2 = os.path.join(json_folder2, filename)
            
            if os.path.exists(file_path2):
                logging.info(f"Processing files: {file_path1} and {file_path2}")
                processor.process_json_files(file_path1, file_path2)
            else:
                logging.warning(f"Corresponding file not found in json2 folder: {filename}")

    # Save any remaining batch requests
    processor.save_current_batch()
    processor.save_request_mapping("j_request_mapping.json")

    # Add this to your main function or wherever you process the LLM responses
    # reconstructed_documents = reconstruct_documents(processor.request_mapping, llm_responses)

    logging.info("Processing completed.")

if __name__ == "__main__":
    main()