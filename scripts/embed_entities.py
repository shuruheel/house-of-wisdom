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

def get_all_entities(tx):
    query = """
    MATCH (e:Entity)
    RETURN id(e) AS id, e.name AS name
    """
    results = list(tx.run(query))
    logging.info(f"Number of entities retrieved: {len(results)}")
    entities = []
    for i, record in enumerate(results):
        entity = {
            'id': record['id'],
            'name': record['name']
        }
        entities.append(entity)
        if i < 5:  # Log first 5 entities
            logging.info(f"Entity {i}: id={entity['id']}, name={entity['name'][:30] if entity['name'] else 'None'}...")
    return entities

def compute_embedding(entity):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            text = entity['name']
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return str(entity['id']), response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to compute embedding for entity {entity['id']} after {max_retries} attempts: {e}")
                return str(entity['id']), None
            time.sleep(2 ** attempt)  # Exponential backoff

def load_existing_embeddings(filename='entity_embeddings.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def generate_embeddings(entities, existing_embeddings):
    embeddings = existing_embeddings.copy()
    entities_to_process = [entity for entity in entities if str(entity['id']) not in embeddings]
    batch_size = 10  # Adjust based on API rate limits and performance
    
    logging.info(f"Found {len(existing_embeddings)} existing embeddings. Processing {len(entities_to_process)} new entities.")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(entities_to_process), batch_size), desc="Processing entities"):
            batch = entities_to_process[i:i+batch_size]
            futures = [executor.submit(compute_embedding, entity) for entity in batch]
            for future in as_completed(futures):
                entity_id, embedding = future.result()
                if embedding:
                    embeddings[entity_id] = embedding
                    logging.info(f"Added embedding for entity ID: {entity_id}")
                else:
                    logging.warning(f"No embedding generated for entity {entity_id}")
            
            # Log progress every 100 batches
            if (i // batch_size) % 100 == 0 and i > 0:
                logging.info(f"Processed {i} new entities. Current embeddings count: {len(embeddings)}")
            
            time.sleep(1)  # Rate limiting
    
    return embeddings

def save_embeddings(embeddings, filename='entity_embeddings.json'):
    with open(filename, 'w') as f:
        json.dump({str(k): v for k, v in embeddings.items()}, f)  # Ensure all keys are strings
    logging.info(f"Saved {len(embeddings)} embeddings to {filename}")

def main():
    with neo4j_driver.session() as session:
        entities = session.execute_read(get_all_entities)
        logging.info(f"Retrieved {len(entities)} entities")
        if entities:
            logging.info(f"Sample entity: {entities[0]}")
    
    neo4j_driver.close()
    logging.info("Neo4j connection closed")
    
    existing_embeddings = load_existing_embeddings()
    embeddings = generate_embeddings(entities, existing_embeddings)
    save_embeddings(embeddings)
    logging.info(f"Generated and saved embeddings for {len(embeddings)} entities")

if __name__ == "__main__":
    main()