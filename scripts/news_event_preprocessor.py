import json
import os
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsEventPreprocessor:
    def __init__(self, input_dir, output_file):
        self.input_dir = input_dir
        self.output_file = output_file
        self.merged_data = defaultdict(list)

    def load_json_files(self):
        for filename in os.listdir(self.input_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.input_dir, filename)
                logger.info(f"Processing file: {filename}")
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    for key in data:
                        self.merged_data[key].extend(data[key])

    def merge_duplicates(self):
        for key in self.merged_data:
            logger.info(f"Merging duplicates for: {key}")
            unique_items = {}
            for item in self.merged_data[key]:
                item_id = self.get_item_id(item, key)
                if item_id in unique_items:
                    unique_items[item_id] = self.merge_items(unique_items[item_id], item)
                else:
                    unique_items[item_id] = item
            self.merged_data[key] = list(unique_items.values())

    def get_item_id(self, item, key):
        if key == 'events':
            return item['name']
        elif key == 'stories':
            return item['name']
        elif key == 'entities':
            return item['name']
        elif key == 'concepts':
            return item['name']
        elif key == 'concept_relationships':
            return f"{item['from']}_{item['to']}_{item['type']}"
        else:
            return json.dumps(item, sort_keys=True)

    def merge_items(self, item1, item2):
        merged = item1.copy()
        for key, value in item2.items():
            if isinstance(value, list):
                merged[key] = list(set(merged.get(key, []) + value))
            elif isinstance(value, dict):
                merged[key] = self.merge_items(merged.get(key, {}), value)
            else:
                # For simple values, keep the non-empty one or the second one if both are non-empty
                merged[key] = value if value or not merged.get(key) else merged[key]
        return merged

    def save_merged_data(self):
        with open(self.output_file, 'w') as f:
            json.dump(dict(self.merged_data), f, indent=2)
        logger.info(f"Merged data saved to: {self.output_file}")

    def print_stats(self):
        for key in self.merged_data:
            logger.info(f"Total {key}: {len(self.merged_data[key])}")

    def process(self):
        self.load_json_files()
        self.merge_duplicates()
        self.save_merged_data()
        self.print_stats()

if __name__ == "__main__":
    input_directory = "news_events"  # Directory containing the news event JSON files
    output_file = "news_events/merged_news_events.json"  # Output file for merged data

    preprocessor = NewsEventPreprocessor(input_directory, output_file)
    preprocessor.process()