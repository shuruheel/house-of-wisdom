import os
import json
import logging
from knowledge_graph_reports import KnowledgeGraphEnhancer
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_and_enhance(data_directory, skip_embeddings=True, max_retries=3, retry_delay=10):
    enhancer = KnowledgeGraphEnhancer(skip_embeddings=skip_embeddings)
    processed_chunks_file = "processed_chunks.json"
    
    if os.path.exists(processed_chunks_file):
        with open(processed_chunks_file, 'r') as f:
            processed_chunks = set(json.load(f))
    else:
        processed_chunks = set()
    
    for root, dirs, files in os.walk(data_directory):
        for file in files:
            if file.startswith('chunk_') and file.endswith('.json'):
                file_path = os.path.join(root, file)
                if file_path not in processed_chunks:
                    logger.info(f"Importing {file_path}")
                    try:
                        enhancer.import_chunk(file_path)
                        processed_chunks.add(file_path)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
                else:
                    logger.info(f"Skipping already processed file: {file_path}")
    
    with open(processed_chunks_file, 'w') as f:
        json.dump(list(processed_chunks), f)
    
    logger.info("All chunks imported successfully")
    
    for attempt in range(max_retries):
        try:
            enhancer.run_enhancement()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to run enhancement after {max_retries} attempts: {str(e)}", exc_info=True)
            else:
                logger.warning(f"Error during enhancement, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
    
    enhancer.close()

if __name__ == "__main__":
    import_and_enhance("data/reports", skip_embeddings=True)