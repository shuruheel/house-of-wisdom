import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
from openai import OpenAI
from tqdm import tqdm
from tqdm.auto import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# Add this line to specify the database
neo4j_database = "god"

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define node types and their embedding fields
NODE_TYPES = {
    "Amendment": "content",
    "Article": "content",
    "Section": "content"
}

def get_nodes(tx, node_type, embedding_field):
    query = f"""
    MATCH (n:{node_type})
    RETURN elementId(n) AS id, n.{embedding_field} AS embedding_text
    """
    results = list(tx.run(query))
    logging.info(f"Number of {node_type} nodes retrieved: {len(results)}")
    nodes = []
    for i, record in enumerate(results):
        node = {
            'id': record['id'],
            'embedding_text': record['embedding_text']
        }
        nodes.append(node)
        if i < 5:  # Log first 5 nodes
            logging.info(f"{node_type} {i}: id={node['id']}, text={node['embedding_text'][:30] if node['embedding_text'] else 'None'}...")
    return nodes

def compute_embedding(node):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            text = node['embedding_text']
            if not text:
                return str(node['id']), None
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return str(node['id']), response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to compute embedding for node {node['id']} after {max_retries} attempts: {e}")
                return str(node['id']), None
            time.sleep(2 ** attempt)  # Exponential backoff

def get_or_create_embedding_chunks(filename, chunk_size=100000):
    """Get existing chunks or create new ones if they don't exist."""
    chunk_dir = f"{os.path.splitext(filename)[0]}_chunks"
    if os.path.exists(chunk_dir):
        chunk_files = [os.path.join(chunk_dir, f) for f in os.listdir(chunk_dir) if f.endswith('.json')]
        if chunk_files:
            logging.info(f"Found {len(chunk_files)} existing chunk files in {chunk_dir}")
            return chunk_files

    # If chunks don't exist, check if the original file exists
    if not os.path.exists(filename):
        logging.info(f"No existing embeddings file found for {filename}")
        return []

    # If original file exists, create chunks
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_files = []
    current_chunk = {}
    chunk_count = 0
    
    logging.info(f"Splitting {filename} into chunks of {chunk_size} embeddings each")
    with open(filename, 'r') as f:
        embeddings = json.load(f)
        for i, (key, value) in enumerate(tqdm(embeddings.items(), desc="Splitting file")):
            current_chunk[key] = value
            if (i + 1) % chunk_size == 0:
                chunk_file = os.path.join(chunk_dir, f"chunk_{chunk_count}.json")
                with open(chunk_file, 'w') as cf:
                    json.dump(current_chunk, cf)
                chunk_files.append(chunk_file)
                current_chunk = {}
                chunk_count += 1
        
        # Write any remaining embeddings
        if current_chunk:
            chunk_file = os.path.join(chunk_dir, f"chunk_{chunk_count}.json")
            with open(chunk_file, 'w') as cf:
                json.dump(current_chunk, cf)
            chunk_files.append(chunk_file)
    
    logging.info(f"Split {filename} into {len(chunk_files)} chunks")
    return chunk_files

def load_existing_embeddings(filename):
    chunk_files = get_or_create_embedding_chunks(filename)
    for chunk_file in chunk_files:
        with open(chunk_file, 'r') as f:
            chunk_embeddings = json.load(f)
        
        # Convert old integer IDs to new elementId format
        new_embeddings = {}
        for key, value in chunk_embeddings.items():
            if ':' not in key:  # Old format (integer ID)
                new_key = f"4:706fb9ad-95c2-4957-890e-2fa2bc86d459:{key}"
                new_embeddings[new_key] = value
            else:  # New format (already in elementId format)
                new_embeddings[key] = value
        
        yield new_embeddings

def generate_embeddings(nodes, existing_embeddings_file, node_type):
    embeddings = {}
    nodes_to_process = []
    
    for chunk_embeddings in load_existing_embeddings(existing_embeddings_file):
        for node in nodes:
            node_id = str(node['id'])
            if node_id in chunk_embeddings:
                embeddings[node_id] = chunk_embeddings[node_id]
            elif node_id not in embeddings:
                nodes_to_process.append(node)
    
    logging.info(f"Found {len(embeddings)} existing embeddings. Processing {len(nodes_to_process)} new nodes.")

    # Process new nodes
    batch_size = 50
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(nodes_to_process), batch_size), desc="Processing nodes"):
            batch = nodes_to_process[i:i+batch_size]
            futures = [executor.submit(compute_embedding, node) for node in batch]
            for future in as_completed(futures):
                node_id, embedding = future.result()
                if embedding:
                    embeddings[node_id] = embedding
                    logging.info(f"Added embedding for node ID: {node_id}")
                else:
                    logging.warning(f"No embedding generated for node {node_id}")
            
            # Save embeddings after each batch
            save_embeddings(embeddings, f"{node_type.lower()}_embeddings_new.json")
            
            if (i // batch_size) % 100 == 0 and i > 0:
                logging.info(f"Processed {i} new nodes. Current embeddings count: {len(embeddings)}")
            
            time.sleep(1)  # Rate limiting
    
    return embeddings

def save_embeddings(embeddings, filename):
    chunk_size = 100000
    chunk_dir = f"{os.path.splitext(filename)[0]}_chunks"
    os.makedirs(chunk_dir, exist_ok=True)
    
    for i in range(0, len(embeddings), chunk_size):
        chunk = dict(list(embeddings.items())[i:i+chunk_size])
        chunk_file = os.path.join(chunk_dir, f"chunk_{i//chunk_size}.json")
        with open(chunk_file, 'w') as f:
            json.dump({str(k): v for k, v in chunk.items()}, f)
    
    logging.info(f"Saved {len(embeddings)} embeddings in chunks to {chunk_dir}")

def remove_embedding_constraints_and_indexes(tx, node_type):
    # Check for any constraints or indexes related to embedding
    result = tx.run("SHOW CONSTRAINTS")
    for record in result:
        if 'embedding' in str(record.get('properties', '')).lower() and node_type in str(record.get('labelsOrTypes', '')):
            tx.run(f"DROP CONSTRAINT {record['name']} IF EXISTS")
            logging.info(f"Dropped constraint: {record['name']}")

    result = tx.run("SHOW INDEXES")
    for record in result:
        if 'embedding' in str(record.get('properties', '')).lower() and node_type in str(record.get('labelsOrTypes', '')):
            tx.run(f"DROP INDEX {record['name']} IF EXISTS")
            logging.info(f"Dropped index: {record['name']}")

    logging.info(f"Removed constraints and indexes on the embedding property for {node_type}")

def update_node_embeddings_batch(tx, node_type, embeddings_batch):
    query = f"""
    UNWIND $embeddings AS embedding
    MATCH (n:{node_type})
    WHERE elementId(n) = embedding.id
    SET n.embedding = embedding.vector
    RETURN count(n) as updated_count, collect(elementId(n)) as updated_ids
    """
    result = tx.run(query, embeddings=[
        {"id": k, "vector": v} for k, v in embeddings_batch.items()
    ])
    record = result.single()
    updated_count = record["updated_count"]
    updated_ids = record["updated_ids"]
    logging.info(f"Batch update: {updated_count} nodes updated. First few IDs: {updated_ids[:5]}")
    return updated_count, updated_ids

def process_node_type(node_type, embedding_field):
    logging.info(f"Processing {node_type} nodes...")
    
    # First, try to upload existing embeddings
    embeddings_file = f"{node_type.lower()}_embeddings.json"
    chunk_files = get_or_create_embedding_chunks(embeddings_file)
    
    if chunk_files:
        upload_existing_embeddings(node_type, embeddings_file)
    else:
        logging.info(f"No existing embeddings found for {node_type}. Will generate new embeddings.")
    
    # Verify the number of nodes with embeddings
    with neo4j_driver.session(database=neo4j_database) as session:
        result = session.run(f"MATCH (n:{node_type}) WHERE n.embedding IS NOT NULL RETURN count(n) as count")
        nodes_with_embeddings = result.single()["count"]
        logging.info(f"{nodes_with_embeddings} {node_type} nodes already have embeddings")
    
    # Then, process nodes without embeddings
    with neo4j_driver.session(database=neo4j_database) as session:
        nodes = session.execute_read(get_nodes_without_embeddings, node_type, embedding_field)
    
    logging.info(f"Found {len(nodes)} {node_type} nodes without embeddings")
    
    if len(nodes) == 0:
        logging.info(f"All {node_type} nodes have embeddings. Skipping embedding generation.")
        return
    
    # Generate and upload new embeddings in batches
    batch_size = 500
    with tqdm(total=len(nodes), desc=f"Processing new {node_type} embeddings") as pbar:
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i+batch_size]
            new_embeddings = generate_embeddings_batch(batch)
            updated_count = upload_embeddings_batch(node_type, new_embeddings)
            
            pbar.update(len(batch))
            
            if (i + batch_size) % (batch_size * 10) == 0:
                logging.info(f"Processed and uploaded {i + batch_size} new embeddings for {node_type}")

    logging.info(f"Completed processing {node_type} nodes")

def upload_existing_embeddings(node_type, embeddings_file):
    chunk_files = get_or_create_embedding_chunks(embeddings_file)
    total_uploaded = 0
    batch_size = 500
    
    with tqdm(total=len(chunk_files), desc=f"Uploading existing {node_type} embeddings (chunks)") as pbar_chunks:
        with neo4j_driver.session(database=neo4j_database) as session:
            for chunk_embeddings in load_existing_embeddings(embeddings_file):
                batches = [list(chunk_embeddings.items())[i:i+batch_size] for i in range(0, len(chunk_embeddings), batch_size)]
                
                with tqdm(total=len(batches), desc=f"Processing chunk {pbar_chunks.n + 1}/{len(chunk_files)}", leave=False) as pbar_batches:
                    for batch in batches:
                        updated_count, updated_ids = session.execute_write(update_node_embeddings_batch, node_type, dict(batch))
                        total_uploaded += updated_count
                        pbar_batches.update(1)
                        if updated_count == 0:
                            logging.warning(f"No nodes were updated in this batch. First few IDs: {[id for id, _ in batch[:5]]}")
                        else:
                            logging.info(f"Batch update: {updated_count} nodes updated. First few IDs: {updated_ids[:5]}")
                
                if total_uploaded % (batch_size * 10) == 0:
                    logging.info(f"Uploaded {total_uploaded} existing embeddings for {node_type}")
                
                pbar_chunks.update(1)
    
    logging.info(f"Total existing {node_type} embeddings uploaded: {total_uploaded}")

    # Verify the upload
    with neo4j_driver.session(database=neo4j_database) as session:
        result = session.run(f"MATCH (n:{node_type}) WHERE n.embedding IS NOT NULL RETURN count(n) as count")
        verified_count = result.single()["count"]
        logging.info(f"Verified {verified_count} nodes with embeddings in the database")
        
        if verified_count != total_uploaded:
            logging.error(f"Mismatch in upload count. Uploaded: {total_uploaded}, Verified: {verified_count}")

def generate_embeddings_batch(nodes):
    embeddings = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(compute_embedding, node) for node in nodes]
        for future in as_completed(futures):
            node_id, embedding = future.result()
            if embedding:
                embeddings[node_id] = embedding
                logging.info(f"Generated embedding for node ID: {node_id}")
            else:
                logging.warning(f"No embedding generated for node {node_id}")
    return embeddings

def upload_embeddings_batch(node_type, embeddings):
    with neo4j_driver.session(database=neo4j_database) as session:
        updated_count, updated_ids = session.execute_write(update_node_embeddings_batch, node_type, embeddings)
    logging.info(f"Uploaded {updated_count} new embeddings for {node_type}")
    return updated_count

def get_nodes_without_embeddings(tx, node_type, embedding_field):
    query = f"""
    MATCH (n:{node_type})
    WHERE n.embedding IS NULL
    RETURN elementId(n) AS id, n.{embedding_field} AS embedding_text
    """
    results = list(tx.run(query))
    logging.info(f"Number of {node_type} nodes without embeddings: {len(results)}")
    nodes = []
    for i, record in enumerate(results):
        node = {
            'id': record['id'],
            'embedding_text': record['embedding_text']
        }
        nodes.append(node)
        if i < 5:  # Log first 5 nodes
            logging.info(f"{node_type} {i}: id={node['id']}, text={node['embedding_text'][:30] if node['embedding_text'] else 'None'}...")
    return nodes

def main():
    for node_type, embedding_field in NODE_TYPES.items():
        process_node_type(node_type, embedding_field)

    neo4j_driver.close()
    logging.info("Neo4j connection closed")

if __name__ == "__main__":
    main()