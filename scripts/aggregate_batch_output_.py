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
        if filename.startswith('batch_output') and filename.endswith('.jsonl'):
            with open(os.path.join(folder_path, filename), 'r') as f:
                for line in f:
                    data = json.loads(line)
                    custom_id = data['custom_id']
                    content_str = data['response']['body']['choices'][0]['message']['content']
                    
                    # Extract JSON from the content string
                    json_match = re.search(r'```json\n(.*?)\n```', content_str, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        try:
                            content = json.loads(json_str)
                            batch_outputs[custom_id] = content
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON for custom_id: {custom_id}")
                    else:
                        print(f"No JSON found in content for custom_id: {custom_id}")
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
        if 'entities' in data[field]:
            return [clean_value(item) for item in data[field]['entities'] if clean_value(item) is not None]
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
            file_path = mapping['file_path']
            
            # Safely get chapter_number, defaulting to '0' if not found
            chapter_number = mapping.get('chapter_number') or '0'
            if not chapter_number:
                chapters = output.get('chapters', [])
                chapter_number = chapters[0].get('chapter_number', '0') if chapters else '0'

            metadata = mapping['metadata']

            # Add metadata to the file if it doesn't exist yet
            if not file_data[file_path]['metadata']:
                file_data[file_path]['metadata'] = {
                    'title': output.get('title', ''),
                    'type': output.get('type', ''),
                    'doc_number': output.get('doc_number', ''),
                    'full_title': output.get('full_title', ''),
                    'enactment_date': output.get('enactment_date', '')
                }

            # Initialize chapter if it doesn't exist
            if chapter_number not in file_data[file_path]['chapters']:
                file_data[file_path]['chapters'][chapter_number] = {
                    'chapter_number': chapter_number,
                    'chapter_title': output.get('chapters', [{}])[0].get('chapter_title', '') if output.get('chapters') else '',
                    'entities': [],
                    'concepts': [],
                    'substantive_provisions': [],
                    'conditions': [],
                    'consequences': []
                }

            # Aggregate fields by chapter
            chapter = file_data[file_path]['chapters'][chapter_number]
            for field in ['entities', 'concepts', 'substantive_provisions', 'conditions', 'consequences']:
                if output.get('chapters'):
                    for section in output['chapters'][0].get('sections', []):
                        chapter[field].extend(section.get(field, []))
                else:
                    chapter[field].extend(extract_field(output, field))

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
                'entities': deduplicate_list(chapter_data['entities']),
                'concepts': deduplicate_list(chapter_data['concepts']),
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