import os
import json
import logging
from collections import defaultdict
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def merge_lists(list1, list2, key):
    """Merge two lists of dictionaries based on a key, avoiding duplicates."""
    merged = {item[key]: item for item in list1}
    for item in list2:
        if item[key] not in merged:
            merged[item[key]] = item
        else:
            # If the item exists, update with non-null values from the new item
            for k, v in item.items():
                if v is not None:
                    merged[item[key]][k] = v
    return list(merged.values())

def merge_chapter_chunks(chapter_dir):
    """Merge all chunk files in a chapter directory into a single JSON file."""
    merged_data = defaultdict(list)
    chunk_files = [f for f in os.listdir(chapter_dir) if f.endswith('.json')]
    
    for chunk_file in chunk_files:
        with open(os.path.join(chapter_dir, chunk_file), 'r') as f:
            chunk_data = json.load(f)
        
        for key in chunk_data:
            if key in ['stories', 'events', 'concepts']:
                merged_data[key] = merge_lists(merged_data[key], chunk_data[key], 'name')
            elif key in ['claims']:
                merged_data[key] = merge_lists(merged_data[key], chunk_data[key], 'content')
            elif key not in ['entities', 'emotional_states']:  # Skip these keys
                merged_data[key].extend(chunk_data[key])
    
    return dict(merged_data)

def natural_sort_key(s):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

def process_book_chapters(book_dir):
    """Process all chapters in a book directory."""
    chapter_items = [d for d in os.listdir(book_dir) if d.startswith('chapter_')]
    
    # Sort items naturally
    chapter_items.sort(key=natural_sort_key)
    
    for chapter_item in chapter_items:
        chapter_path = os.path.join(book_dir, chapter_item)
        if os.path.isdir(chapter_path):
            logger.info(f"Processing directory: {chapter_item}")
            merged_chapter = merge_chapter_chunks(chapter_path)
            output_file = os.path.join(book_dir, f"{chapter_item}.json")
        elif chapter_item.endswith('.json'):
            logger.info(f"Processing file: {chapter_item}")
            with open(chapter_path, 'r') as f:
                merged_chapter = json.load(f)
            output_file = chapter_path
        else:
            logger.warning(f"Skipping unexpected item: {chapter_item}")
            continue
        
        with open(output_file, 'w') as f:
            json.dump(merged_chapter, f, indent=2)
        
        logger.info(f"Processed: {output_file}")

def main():
    data_dir = "data/metadata"
    book_dirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
    
    for book_dir in book_dirs:
        logger.info(f"Processing book: {book_dir}")
        process_book_chapters(os.path.join(data_dir, book_dir))

if __name__ == "__main__":
    main()