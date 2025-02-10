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

def get_all_events(tx):
    query = "MATCH (e:Event) RETURN e.name AS name, e.description AS description"
    results = list(tx.run(query))
    logging.info(f"Number of events retrieved: {len(results)}")
    events = []
    for i, record in enumerate(results):
        name = record['name']
        description = record['description']
        # Create a composite ID using name and description
        composite_id = hashlib.md5(f"{name}{description}".encode()).hexdigest()
        event = {
            'id': composite_id,
            'name': name,
            'description': description
        }
        events.append(event)
        if i < 5:  # Log first 5 events
            logging.info(f"Event {i}: id={composite_id[:8]}..., name={name[:30] if name else 'None'}...")
    return events

def compute_embedding(event):
    max_retries = 3
    logging.info(f"Processing event: id={event.get('id')}, name={event.get('name')[:30]}...")
    for attempt in range(max_retries):
        try:
            text = f"{event['name']} {event['description']}"
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return str(event['id']), response.data[0].embedding
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed to compute embedding for event {event['id']} after {max_retries} attempts: {e}")
                return str(event['id']), None
            time.sleep(2 ** attempt)  # Exponential backoff

def load_existing_embeddings(filename='event_embeddings.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def generate_embeddings(events, existing_embeddings):
    embeddings = existing_embeddings.copy()
    events_to_process = [event for event in events if event['id'] not in embeddings]
    batch_size = 100  # Adjust based on API rate limits and performance
    
    logging.info(f"Found {len(existing_embeddings)} existing embeddings. Processing {len(events_to_process)} new events.")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i in tqdm(range(0, len(events_to_process), batch_size), desc="Processing events"):
            batch = events_to_process[i:i+batch_size]
            futures = [executor.submit(compute_embedding, event) for event in batch]
            for future in as_completed(futures):
                event_id, embedding = future.result()
                if embedding:
                    embeddings[event_id] = embedding
                    logging.info(f"Added embedding for event ID: {event_id}")
                else:
                    logging.warning(f"No embedding generated for event {event_id}")
            
            # Log progress every 100 batches
            if (i // batch_size) % 100 == 0 and i > 0:
                logging.info(f"Processed {i} new events. Current embeddings count: {len(embeddings)}")
            
            time.sleep(1)  # Rate limiting
    
    return embeddings

def save_embeddings(embeddings, filename='event_embeddings.json'):
    with open(filename, 'w') as f:
        json.dump({str(k): v for k, v in embeddings.items()}, f)  # Ensure all keys are strings
    logging.info(f"Saved {len(embeddings)} embeddings to {filename}")

def main():
    with neo4j_driver.session() as session:
        events = session.execute_read(get_all_events)
        logging.info(f"Retrieved {len(events)} events")
        if events:
            logging.info(f"Sample event: {events[0]}")
    
    neo4j_driver.close()
    logging.info("Neo4j connection closed")
    
    existing_embeddings = load_existing_embeddings()
    embeddings = generate_embeddings(events, existing_embeddings)
    save_embeddings(embeddings)
    logging.info(f"Generated and saved embeddings for {len(embeddings)} events")

if __name__ == "__main__":
    main()