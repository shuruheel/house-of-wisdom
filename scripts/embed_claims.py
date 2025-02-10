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

def get_all_claims(tx):
    query = "MATCH (c:Claim) RETURN c.source AS source, c.content AS content"
    results = list(tx.run(query))
    logging.info(f"Number of claims retrieved: {len(results)}")
    claims = []
    for i, record in enumerate(results):
        source = record['source'] or ''
        content = record['content'] or ''
        if source == '' and content == '':
            logging.warning(f"Skipping claim with empty source and content")
            continue
        # Create a composite ID using source and content
        composite_id = hashlib.md5(f"{source}{content}".encode()).hexdigest()
        claim = {
            'id': composite_id,
            'source': source,
            'content': content
        }
        claims.append(claim)
        if i < 5:  # Log first 5 claims
            logging.info(f"Claim {i}: id={composite_id[:8]}..., source={source[:30]}...")
    return claims

def compute_embedding(claim):
    max_retries = 3
    logging.info(f"Processing claim: id={claim['id']}, content={claim['content'][:30]}...")
    for attempt in range(max_retries):
        try:
            text = claim['content'].strip()
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return str(claim['id']), response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to compute embedding for claim {claim['id']} after {max_retries} attempts: {e}")
                return str(claim['id']), None
            time.sleep(2 ** attempt)  # Exponential backoff

def generate_embeddings(claims):
    embeddings = {}
    batch_size = 100  # Adjust based on API rate limits and performance
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(claims), batch_size), desc="Processing claims"):
            batch = claims[i:i+batch_size]
            futures = [executor.submit(compute_embedding, claim) for claim in batch]
            for future in as_completed(futures):
                claim_id, embedding = future.result()
                logging.info(f"Processed claim ID: {claim_id}")
                if embedding:
                    embeddings[claim_id] = embedding
                    logging.info(f"Added embedding for claim ID: {claim_id}")
                else:
                    logging.warning(f"No embedding generated for claim {claim_id}")
            
            # Log progress every 100 batches
            if (i // batch_size) % 100 == 0 and i > 0:
                logging.info(f"Processed {i} claims. Current embeddings count: {len(embeddings)}")
            
            time.sleep(1)  # Rate limiting
    
    return embeddings

def save_embeddings(embeddings, filename='claim_embeddings.json'):
    with open(filename, 'w') as f:
        json.dump({str(k): v for k, v in embeddings.items()}, f)  # Ensure all keys are strings
    logging.info(f"Saved {len(embeddings)} embeddings to {filename}")

def main():
    with neo4j_driver.session() as session:
        claims = session.execute_read(get_all_claims)
        logging.info(f"Retrieved {len(claims)} claims")
        if claims:
            logging.info(f"Sample claim: {claims[0]}")
    
    neo4j_driver.close()
    logging.info("Neo4j connection closed")
    
    embeddings = generate_embeddings(claims)
    save_embeddings(embeddings)
    logging.info(f"Generated and saved embeddings for {len(embeddings)} claims")

if __name__ == "__main__":
    main()