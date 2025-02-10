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

def load_embeddings(filename='entity_embeddings.json'):
    with open(filename, 'r') as f:
        return json.load(f)

def remove_embedding_constraints_and_indexes(tx):
    # Drop the specific constraint we know exists
    tx.run("DROP CONSTRAINT constraint_9a18acc8 IF EXISTS")
    logging.info("Dropped constraint on Entity.embedding if it existed")

    # Check for any other constraints or indexes related to embedding
    result = tx.run("SHOW CONSTRAINTS")
    for record in result:
        if 'embedding' in str(record.get('properties', '')).lower():
            tx.run(f"DROP CONSTRAINT {record['name']} IF EXISTS")
            logging.info(f"Dropped additional constraint: {record['name']}")

    result = tx.run("SHOW INDEXES")
    for record in result:
        if 'embedding' in str(record.get('properties', '')).lower():
            tx.run(f"DROP INDEX {record['name']} IF EXISTS")
            logging.info(f"Dropped index: {record['name']}")

    logging.info("Removed constraints and indexes on the embedding property")

def update_entity_embeddings_batch(tx, embeddings_batch):
    query = """
    UNWIND $embeddings AS embedding
    MATCH (e:Entity)
    WHERE id(e) = toInteger(embedding.id)
    SET e.embedding = embedding.vector
    """
    tx.run(query, embeddings=[
        {"id": k, "vector": v} for k, v in embeddings_batch.items()
    ])

def main():
    embeddings = load_embeddings()
    logging.info(f"Loaded {len(embeddings)} embeddings")
    
    with neo4j_driver.session() as session:
        session.execute_write(remove_embedding_constraints_and_indexes)
    
    batch_size = 100  # Reduced batch size
    total_processed = 0
    
    with neo4j_driver.session() as session:
        for i in tqdm(range(0, len(embeddings), batch_size), desc="Processing batches"):
            batch = dict(list(embeddings.items())[i:i+batch_size])
            session.execute_write(update_entity_embeddings_batch, batch)
            total_processed += len(batch)
            
            if i % (batch_size * 10) == 0 and i > 0:
                logging.info(f"Processed {total_processed} embeddings.")

    logging.info(f"Total entity embeddings processed: {total_processed}")

    neo4j_driver.close()
    logging.info("Neo4j connection closed")

if __name__ == "__main__":
    main()