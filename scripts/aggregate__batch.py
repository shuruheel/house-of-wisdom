import json
import os
import re
from collections import defaultdict

def extract_json(file_content):
    try:
        # Find the start and end of the JSON object
        start = file_content.index('{')
        end = file_content.rindex('}') + 1
        
        # Extract the JSON string
        json_str = file_content[start:end]
        
        # Parse the JSON string
        return json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error extracting JSON: {e}")
        return None
    
def load_request_mapping(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    json_data = extract_json(content)
    if json_data:
        return(json_data)

def load_batch_outputs(folder_path='.'):
    batch_outputs = {}
    for filename in os.listdir(folder_path):
        if filename.startswith('j_batch_output') and filename.endswith('.jsonl'):
            with open(os.path.join(folder_path, filename), 'r') as f:
                for line in f:
                    data = json.loads(line)
                    custom_id = data['custom_id']
                    content_str = data['response']['body']['choices'][0]['message']['content']
                    
                    try:
                        content = json.loads(content_str)
                        batch_outputs[custom_id] = content
                    except json.JSONDecodeError:
                        print(f"Failed to parse JSON for custom_id: {custom_id}")
    return batch_outputs

def clean_value(value):
    if isinstance(value, str):
        # Remove single-character values that are not 'a' or 'A'
        if len(value) == 1 and value.lower() != 'a':
            return None
        # Remove leading/trailing whitespace and quotes
        return value.strip().strip('"\'')
    return value

def merge_dicts(dict1, dict2):
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                result[key] = deduplicate_list(result[key] + value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result

def extract_field(data, field):
    if isinstance(data.get(field), list):
        return [clean_value(item) for item in data[field] if clean_value(item) is not None]
    elif isinstance(data.get(field), dict):
        if 'scope' in data[field]:
            return [clean_value(item) for item in data[field]['scope'] if clean_value(item) is not None]
        else:
            return [clean_value(data[field])]
    return []

def deduplicate_list(lst):
    def make_hashable(item):
        if isinstance(item, (list, tuple)):
            return tuple(make_hashable(i) for i in item)
        elif isinstance(item, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in item.items()))
        else:
            return item

    seen = set()
    result = []
    for item in lst:
        hashable_item = make_hashable(item)
        if hashable_item not in seen:
            seen.add(hashable_item)
            result.append(item)
    return result

def process_outputs(request_mapping, batch_outputs):
    file_data = defaultdict(lambda: {'metadata': {}, 'chapters': defaultdict(dict)})

    for request_id, mapping in request_mapping.items():
        if request_id in batch_outputs:
            output = batch_outputs[request_id]
            
            # Check if 'file_path' exists in the mapping
            if 'file_path' not in mapping:
                print(f"Warning: 'file_path' not found for request_id: {request_id}. Skipping this entry.")
                continue
            
            file_path = mapping['file_path']
            
            chapter_number = mapping.get('chapter_number') or '0'

            # Add metadata to the file if it doesn't exist yet
            if not file_data[file_path]['metadata']:
                file_data[file_path]['metadata'] = {
                    'title': mapping['metadata'].get('title', ''),
                    'type': mapping['metadata'].get('type', ''),
                    'doc_number': mapping['metadata'].get('doc_number', ''),
                    'full_title': mapping['metadata'].get('full_title', ''),
                    'enactment_date': mapping['metadata'].get('enactment_date', '')
                }

            # Initialize chapter if it doesn't exist
            if chapter_number not in file_data[file_path]['chapters']:
                file_data[file_path]['chapters'][chapter_number] = {
                    'chapter_number': chapter_number,
                    'chapter_title': mapping['metadata'].get('chapter_title', ''),
                    'scope': [],
                    'definitions': [],
                    'substantive_provisions': [],
                    'conditions': [],
                    'consequences': []
                }

            # Aggregate fields by chapter
            chapter = file_data[file_path]['chapters'][chapter_number]
            
            if 'extracted_data' in output:
                for section in output['extracted_data']:
                    if 'sections' in section:
                        for subsection in section['sections']:
                            chapter['scope'].extend(subsection.get('scope', []))
                            chapter['definitions'].extend(subsection.get('definitions', []))
                            chapter['substantive_provisions'].extend(subsection.get('substantive_provisions', []))
                            chapter['conditions'].extend(subsection.get('conditions', []))
                            chapter['consequences'].extend(subsection.get('consequences', []))

    # Convert defaultdict to regular dict and deduplicate lists
    result = {}
    for file_path, data in file_data.items():
        result[file_path] = {
            'title': data['metadata'].get('title', ''),
            'type': data['metadata'].get('type', ''),
            'doc_number': data['metadata'].get('doc_number', ''),
            'full_title': data['metadata'].get('full_title', ''),
            'enactment_date': data['metadata'].get('enactment_date', ''),
            'chapters': []
        }
        for chapter_number, chapter_data in sorted(data['chapters'].items()):
            chapter = {
                'chapter_number': chapter_data['chapter_number'],
                'chapter_title': chapter_data['chapter_title'],
                'scope': deduplicate_list(chapter_data['scope']),
                'definitions': deduplicate_list(chapter_data['definitions']),
                'substantive_provisions': deduplicate_list(chapter_data['substantive_provisions']),
                'conditions': deduplicate_list(chapter_data['conditions']),
                'consequences': deduplicate_list(chapter_data['consequences'])
            }
            result[file_path]['chapters'].append(chapter)

    return result

def save_json_files(file_data, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for file_path, chapters in file_data.items():
        output_data = {
            'file_path': file_path,
            'chapters': []
        }

        for chapter_index, chunks in sorted(chapters.items()):
            chapter_data = {
                'chapter_index': chapter_index,
                'chunks': sorted(chunks, key=lambda x: x['chunk_index'])
            }
            output_data['chapters'].append(chapter_data)

        output_filename = os.path.splitext(os.path.basename(file_path))[0] + '.json'
        output_path = os.path.join(output_folder, output_filename)

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

def main():
    request_mapping = load_request_mapping('j_request_mapping.json')
    batch_outputs = load_batch_outputs()
    processed_data = process_outputs(request_mapping, batch_outputs)

    # Create the output directory if it doesn't exist
    output_dir = os.path.join('constitution', 'j_json')
    os.makedirs(output_dir, exist_ok=True)

    # Write the processed data to JSON files
    for file_path, data in processed_data.items():
        # Extract the USC number from the file name
        usc_number = os.path.basename(file_path).split('.')[0]
        output_file = f"{usc_number}.json"
        output_path = os.path.join(output_dir, output_file)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    print("Processing complete. Output files have been created in the constitution/j_json folder.")

if __name__ == '__main__':
    main()