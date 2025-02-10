import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
from openai import OpenAI
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import hashlib
import os.path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_all_concepts(tx):
    query = "MATCH (e:Concept) RETURN e.name AS name"
    results = list(tx.run(query))
    logging.info(f"Number of concepts retrieved: {len(results)}")
    concepts = []
    for i, record in enumerate(results):
        name = record['name']
        # Create a composite ID using name
        composite_id = hashlib.md5(f"{name}".encode()).hexdigest()
        concept = {
            'id': composite_id,
            'name': name
        }
        concepts.append(concept)
        if i < 5:  # Log first 5 concepts
            logging.info(f"Concept {i}: id={composite_id[:8]}..., name={name[:30] if name else 'None'}...")
    return concepts

def compute_embedding(concept):
    max_retries = 3
    logging.info(f"Processing concept: id={concept.get('id')}, name={concept.get('name')[:30]}...")
    for attempt in range(max_retries):
        try:
            text = f"{concept['name']}"
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return str(concept['id']), response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to compute embedding for concept {concept['id']} after {max_retries} attempts: {e}")
                return str(concept['id']), None
            time.sleep(2 ** attempt)  # Exponential backoff

def load_existing_embeddings(filename='concept_embeddings.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def generate_embeddings(concepts, existing_embeddings):
    embeddings = existing_embeddings.copy()
    concepts_to_process = [concept for concept in concepts if concept['id'] not in embeddings]
    batch_size = 10  # Adjust based on API rate limits and performance
    
    logging.info(f"Found {len(existing_embeddings)} existing embeddings. Processing {len(concepts_to_process)} new concepts.")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(concepts_to_process), batch_size), desc="Processing concepts"):
            batch = concepts_to_process[i:i+batch_size]
            futures = [executor.submit(compute_embedding, concept) for concept in batch]
            for future in as_completed(futures):
                concept_id, embedding = future.result()
                if embedding:
                    embeddings[concept_id] = embedding
                    logging.info(f"Added embedding for concept ID: {concept_id}")
                else:
                    logging.warning(f"No embedding generated for concept {concept_id}")
            
            # Log progress every 100 batches
            if (i // batch_size) % 100 == 0 and i > 0:
                logging.info(f"Processed {i} new concepts. Current embeddings count: {len(embeddings)}")
            
            time.sleep(1)  # Rate limiting
    
    return embeddings

def save_embeddings(embeddings, filename='concept_embeddings.json'):
    with open(filename, 'w') as f:
        json.dump({str(k): v for k, v in embeddings.items()}, f)  # Ensure all keys are strings
    logging.info(f"Saved {len(embeddings)} embeddings to {filename}")

def main():
    with neo4j_driver.session() as session:
        concepts = session.execute_read(get_all_concepts)
        logging.info(f"Retrieved {len(concepts)} concepts")
        if concepts:
            logging.info(f"Sample concept: {concepts[0]}")
    
    neo4j_driver.close()
    logging.info("Neo4j connection closed")
    
    existing_embeddings = load_existing_embeddings()
    embeddings = generate_embeddings(concepts, existing_embeddings)
    save_embeddings(embeddings)
    logging.info(f"Generated and saved embeddings for {len(embeddings)} concepts")

if __name__ == "__main__":
    main()