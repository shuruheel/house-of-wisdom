from collections import defaultdict
import json
import os
import logging
import re

def clean_json(json_str):
    # Remove all control characters (including newlines) except space
    json_str = ''.join(char for char in json_str if ord(char) >= 32)
    
    # Replace newlines and other whitespace with a single space
    json_str = re.sub(r'\s+', ' ', json_str)
    
    # Remove trailing commas from lists and objects
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    return json_str

def parse_truncated_json(json_str):
    # Find the last complete object
    last_brace = json_str.rfind('}')
    if last_brace == -1:
        return None
    
    # Try to parse the content up to the last complete object
    try:
        return json.loads(json_str[:last_brace+1])
    except json.JSONDecodeError:
        # If that fails, try to find the last complete section
        section_pattern = r'{\s*"section_number":[^}]+}'
        sections = list(re.finditer(section_pattern, json_str))
        if sections:
            last_section = sections[-1].group()
            truncated_json = f'{{"sections": [{last_section}]}}'
            return json.loads(truncated_json)
    return None

def load_batch_outputs(folder_path='.'):
    batch_outputs = {}
    for filename in os.listdir(folder_path):
        if filename.startswith('batch_output') and filename.endswith('.jsonl'):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r') as f:
                    for line_number, line in enumerate(f, 1):
                        try:
                            data = json.loads(line)
                            custom_id = data.get('custom_id')
                            if not custom_id:
                                logging.warning(f"Missing custom_id in {filename}, line {line_number}")
                                continue

                            content_str = data.get('response', {}).get('body', {}).get('choices', [{}])[0].get('message', {}).get('content')
                            if not content_str:
                                logging.warning(f"Missing content for custom_id: {custom_id} in {filename}, line {line_number}")
                                continue

                            try:
                                content = json.loads(content_str)
                                batch_outputs[custom_id] = content
                            except json.JSONDecodeError:
                                logging.error(f"Failed to parse content JSON for custom_id: {custom_id} in {filename}, line {line_number}")
                                logging.error(f"Problematic content: {content_str[:500]}...")
                        except json.JSONDecodeError:
                            logging.error(f"Failed to parse outer JSON in {filename}, line {line_number}")
                            logging.error(f"Problematic line: {line[:500]}...")
                        except Exception as e:
                            logging.error(f"Error processing line in {filename}, line {line_number}: {str(e)}")
            except IOError:
                logging.error(f"Error reading file: {file_path}")
    return batch_outputs

def load_request_mapping(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Error: {file_path} is not a valid JSON file.")
        return {}
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return {}

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

def normalize_chapter_number(chapter_number):
    # Remove any non-alphanumeric characters and convert to uppercase
    return ''.join(char.upper() for char in chapter_number if char.isalnum())

def process_outputs(request_mapping, batch_outputs):
    file_data = defaultdict(lambda: {'chapters': {}})

    for request_id, mapping in request_mapping.items():
        if request_id in batch_outputs:
            output = batch_outputs[request_id]
            file_path = mapping['file_path']
            
            # Add metadata to the file if it doesn't exist yet
            if 'metadata' not in file_data[file_path]:
                file_data[file_path].update({
                    'title': mapping['metadata'].get('title', ''),
                    'type': mapping['metadata'].get('type', ''),
                    'doc_number': mapping['metadata'].get('doc_number', ''),
                    'full_title': mapping['metadata'].get('full_title', ''),
                    'enactment_date': mapping['metadata'].get('enactment_date', '')
                })

            # Process chapter data
            chapter_number = output.get('chapter_number', '')
            chapter_title = output.get('chapter_title', '')
            if not chapter_number:
                logging.warning(f"Missing chapter_number for request_id: {request_id}")
                continue

            # Normalize the chapter number
            normalized_chapter_number = normalize_chapter_number(chapter_number)
            chapter_key = (normalized_chapter_number, chapter_title)

            if chapter_key not in file_data[file_path]['chapters']:
                file_data[file_path]['chapters'][chapter_key] = {
                    'chapter_number': chapter_number,  # Keep the original format for display
                    'chapter_title': chapter_title,
                    'scope': [],
                    'definitions': [],
                    'substantive_provisions': [],
                    'conditions': [],
                    'consequences': []
                }

            for section in output.get('sections', []):
                section_number = section.get('section_number', '')
                section_title = section.get('section_title', '')
                
                for field in ['scope', 'definitions', 'substantive_provisions', 'conditions', 'consequences']:
                    for item in section.get(field, []):
                        file_data[file_path]['chapters'][chapter_key][field].append({
                            f"{field}_text": item,
                            'section_number': section_number,
                            'section_title': section_title
                        })

    # Convert the nested defaultdict to a regular dict structure
    for file_path, data in file_data.items():
        data['chapters'] = list(data['chapters'].values())

    return dict(file_data)

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
    request_mapping = load_request_mapping('request_mapping.json')
    batch_outputs = load_batch_outputs()
    processed_data = process_outputs(request_mapping, batch_outputs)

    # Create the output directory if it doesn't exist
    output_dir = os.path.join('constitution', 'json')
    os.makedirs(output_dir, exist_ok=True)

    # Write the processed data to JSON files
    for file_path, data in processed_data.items():
        # Extract the USC number from the file name
        usc_number = os.path.basename(file_path).split('.')[0]
        output_file = f"{usc_number}.json"
        output_path = os.path.join(output_dir, output_file)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    print("Processing complete. Output files have been created in the constitution/json folder.")

if __name__ == '__main__':
    main()