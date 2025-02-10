import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
import logging
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

def load_embeddings(filename='event_embeddings.json'):
    with open(filename, 'r') as f:
        return json.load(f)

def get_processed_events(tx):
    query = """
    MATCH (e:Event) 
    WHERE e.embedding IS NOT NULL 
    RETURN apoc.util.md5([e.name, e.description]) AS id
    """
    return [record["id"] for record in tx.run(query)]

def update_event_embeddings_batch(tx, embeddings_batch):
    query = """
    UNWIND $embeddings AS embedding
    MATCH (e:Event)
    WHERE apoc.util.md5([e.name, e.description]) = embedding.id
      AND e.embedding IS NULL
    SET e.embedding = embedding.vector
    RETURN count(*) as updated_count
    """
    result = tx.run(query, embeddings=embeddings_batch)
    return result.single()["updated_count"]

def main():
    embeddings = load_embeddings()
    logging.info(f"Loaded {len(embeddings)} embeddings")
    
    with neo4j_driver.session() as session:
        processed_events = session.execute_read(get_processed_events)
    logging.info(f"Found {len(processed_events)} already processed events")
    
    embeddings_to_process = {k: v for k, v in embeddings.items() if k not in processed_events}
    logging.info(f"Remaining embeddings to process: {len(embeddings_to_process)}")
    
    batch_size = 200
    total_updated = 0
    
    with neo4j_driver.session() as session:
        for i in tqdm(range(0, len(embeddings_to_process), batch_size), desc="Processing batches"):
            batch = dict(list(embeddings_to_process.items())[i:i+batch_size])
            embeddings_batch = [{"id": k, "vector": v} for k, v in batch.items()]
            updated_count = session.execute_write(update_event_embeddings_batch, embeddings_batch)
            total_updated += updated_count
            
            if i % (batch_size * 10) == 0 and i > 0:
                logging.info(f"Processed {i} embeddings. Total updated so far: {total_updated}")

    logging.info(f"Total event embeddings updated in Neo4j: {total_updated}")

    neo4j_driver.close()
    logging.info("Neo4j connection closed")

if __name__ == "__main__":
    main()