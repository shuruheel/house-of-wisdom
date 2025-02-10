import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compute_embeddings(text):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to compute embedding after {max_retries} attempts: {e}")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff

def process_chunk(chunk_path):
    try:
        with open(chunk_path, 'r') as f:
            chunk_text = f.read()
        
        embedding = compute_embeddings(chunk_text)
        return chunk_path, embedding
    except Exception as e:
        print(f"Error processing {chunk_path}: {e}")
        return chunk_path, None

def process_chunks():
    embeddings = {}
    data_dir = 'data/metadata'
    chunk_paths = []
    
    for book_name in os.listdir(data_dir):
        book_path = os.path.join(data_dir, book_name)
        if os.path.isdir(book_path):
            for chapter in os.listdir(book_path):
                chapter_path = os.path.join(book_path, chapter)
                if os.path.isdir(chapter_path):
                    for chunk_file in os.listdir(chapter_path):
                        if chunk_file.endswith('.txt'):
                            chunk_paths.append(os.path.join(chapter_path, chunk_file))
    
    batch_size = 10  # Adjust based on API rate limits and performance
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(chunk_paths), batch_size), desc="Processing chunks"):
            batch = chunk_paths[i:i+batch_size]
            futures = [executor.submit(process_chunk, path) for path in batch]
            for future in as_completed(futures):
                chunk_path, embedding = future.result()
                if embedding:
                    embeddings[chunk_path] = embedding
            time.sleep(1)  # Rate limiting

    with open('chunk_embeddings.json', 'w') as f:
        json.dump(embeddings, f)

if __name__ == "__main__":
    process_chunks()