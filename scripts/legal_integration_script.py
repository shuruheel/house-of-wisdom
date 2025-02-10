import json
import math
import os
import pickle
from dotenv import load_dotenv
from neo4j import GraphDatabase
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import spacy
from tqdm import tqdm
import time
import gc
import hashlib
from neo4j.exceptions import TransientError
import logging
from neo4j.exceptions import ServiceUnavailable, SessionExpired
import re

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load spaCy NER model
nlp = spacy.load("en_core_web_sm")

# Constants
BATCH_SIZE = 100
REVIEW_BATCH_SIZE = 20
MAIN_CHECKPOINT_FILE = "integration_checkpoint.pkl"
UPLOAD_CHECKPOINT_FILE = "upload_checkpoint.json"
SIMILARITY_CHECKPOINT_FILE = "similarity_checkpoint.pkl"
UPDATE_CHECKPOINT_FILE = "update_checkpoint.json"
FIELDS_TO_PROCESS = ['scope', 'definitions']

def get_embedding(text):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(20)
            else:
                raise e

def load_local_embeddings():
    embeddings = {}
    id_to_name = {}
    embedding_to_name = {}

    # Load entity embeddings
    with open('entity_embeddings.json', 'r') as f:
        entity_data = json.load(f)
        for hashed_id, embedding in entity_data.items():
            embedding_array = np.array(embedding, dtype=np.float32)
            embeddings[hashed_id] = embedding_array
            embedding_to_name[tuple(embedding_array)] = hashed_id

    # Load concept embeddings
    with open('concept_embeddings.json', 'r') as f:
        concept_data = json.load(f)
        for hashed_id, embedding in concept_data.items():
            embedding_array = np.array(embedding, dtype=np.float32)
            embeddings[hashed_id] = embedding_array
            embedding_to_name[tuple(embedding_array)] = hashed_id

    # Recreate the id_to_name mapping for both entities and concepts
    with driver.session() as session:
        results = session.run("MATCH (n) WHERE n:Entity OR n:Concept RETURN n.name AS name, n.description AS description, labels(n) AS labels")
        for record in results:
            name = record['name']
            description = record['description']
            label = record['labels'][0]  # Assuming each node has only one label (Entity or Concept)
            composite_id = hashlib.md5(f"{name}{description}".encode()).hexdigest()
            id_to_name[composite_id] = f"{label}: {name}"

    return embeddings, id_to_name, embedding_to_name

# Load local embeddings
local_embeddings, id_to_name, embedding_to_name = load_local_embeddings()

def find_best_match(embedding, threshold=0.5):
    similarities = cosine_similarity([embedding], list(local_embeddings.values()))[0]
    best_match_index = np.argmax(similarities)
    if similarities[best_match_index] > threshold:
        best_match_embedding = tuple(list(local_embeddings.values())[best_match_index])
        best_match_id = embedding_to_name.get(best_match_embedding, "Unknown")
        return id_to_name.get(best_match_id, best_match_id), similarities[best_match_index]
    return None, 0

def load_legal_data(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            with open(os.path.join(directory, filename), 'r') as file:
                yield json.load(file)

def process_field(field_data, field_type):
    if field_type == 'scope':
        content = field_data.get('scope_text', '')
    elif field_type == 'definitions':
        content = field_data.get('definitions_text', '')
    else:
        content = field_data.get('content', '')  # Fallback for other field types
    
    if not content:
        return None  # Skip empty fields

    field_embedding = get_embedding(content)
    match, similarity = find_best_match(field_embedding)
    if match:
        return (field_type, content, 'Entity', match, similarity)
    else:
        return (field_type, content, None, None, 0)

def process_legal_data(document):
    matches = []
    new_entries = []
    legal_structure = {
        "legal_code": {
            "name": document['full_title'],
            "jurisdiction": "United States",
            "government_level": "Federal",
            "doc_number": document['doc_number']
        },
        "chapters": []
    }
    
    for chapter in document['chapters']:
        chapter_data = {
            "chapter_number": chapter['chapter_number'],
            "chapter_title": chapter['chapter_title'],
            "effective_date": document.get('enactment_date', ''),
            "scopes": [],
            "definitions": []
        }
        
        for field_type in FIELDS_TO_PROCESS:
            if field_type in chapter:
                for field_data in chapter[field_type]:
                    result = process_field(field_data, field_type)
                    if result:
                        if result[2]:  # If a match was found
                            matches.append(result)
                        else:
                            new_entries.append((result[0], result[1]))
                        
                        if field_type == 'scope':
                            chapter_data['scopes'].append({
                                "content": field_data['scope_text'],
                                "section_number": field_data['section_number'],
                                "section_title": field_data['section_title']
                            })
                        elif field_type == 'definitions':
                            chapter_data['definitions'].append({
                                "content": field_data['definitions_text'],
                                "section_number": field_data['section_number'],
                                "section_title": field_data['section_title']
                            })
        
        legal_structure['chapters'].append(chapter_data)
    
    return matches, new_entries, legal_structure

def extract_entities_with_ner(text):
    doc = nlp(text)
    return [ent.text for ent in doc.ents]

def batch_review_new_entries(new_entries, batch_size):
    approved_entries = []
    for i in range(0, len(new_entries), batch_size):
        batch = new_entries[i:i+batch_size]
        print(f"\nReviewing batch {i//batch_size + 1} of {len(new_entries)//batch_size + 1}")
        
        for j, (field_type, entry) in enumerate(batch):
            print(f"\nEntry {j+1} of {len(batch)}:")
            print(f"Field type: {field_type}")
            print(f"Content: {entry[:100]}...")  # Show first 100 characters
            
            extracted_entities = extract_entities_with_ner(entry)
            print("Extracted entities:", ", ".join(extracted_entities[:5]))  # Show first 5 entities
            
            entry_embedding = get_embedding(entry)
            similarities = cosine_similarity([entry_embedding], list(local_embeddings.values()))[0]
            top_5_indices = np.argsort(similarities)[-5:][::-1]
            print("Top 5 similar existing entities/concepts:")
            for k, idx in enumerate(top_5_indices):
                similarity = similarities[idx]
                if similarity >= 0.35:  # Increased similarity threshold
                    embedding = tuple(list(local_embeddings.values())[idx])
                    entity_id = embedding_to_name.get(embedding, "Unknown")
                    entity_name = id_to_name.get(entity_id, entity_id)
                    print(f"{k+1}. {entity_name} (Similarity: {similarity:.2f})")
                else:
                    print(f"{k+1}. No match above threshold")
        
        choice = input("\nDoes this batch look good? (y/n): ")
        if choice.lower() == 'y':
            approved_entries.extend(batch)
            print("Batch approved. Entries will be connected to the most similar entities/concepts or new ones will be created.")
        else:
            print("Batch rejected. Please review the data and processing steps.")
            return None
    
    return approved_entries

def automated_entity_matching(new_entries):
    approved_entries = []
    for field_type, entry in new_entries:
        entry_embedding = get_embedding(entry)
        match, similarity = find_best_match(entry_embedding, threshold=0.85)
        if match:
            approved_entries.append((field_type, entry, match, similarity))
        else:
            extracted_entities = extract_entities_with_ner(entry)
            if extracted_entities:
                approved_entries.append((field_type, entry, extracted_entities[0], 0))
            else:
                new_entity_name = " ".join(entry.split()[:5])  # First 5 words
                approved_entries.append((field_type, entry, new_entity_name, 0))
    return approved_entries

def update_graph(driver, matches, new_entries, legal_structure):
    checkpoint = load_update_checkpoint()
    processed_matches = checkpoint["processed_matches"]
    processed_new_entries = checkpoint["processed_new_entries"]

    with driver.session() as session:
        # Create legal code structure
        session.run("""
            MERGE (lc:LegalCode {doc_number: $doc_number})
            SET lc.name = $name,
                lc.jurisdiction = $jurisdiction,
                lc.government_level = $government_level
        """, legal_structure["legal_code"])

        # Create relationships for matches
        for i in tqdm(range(processed_matches, len(matches), BATCH_SIZE), desc="Updating matches"):
            batch = matches[i:i+BATCH_SIZE]
            if batch:  # Only process if batch is not empty
                session.run("""
                    UNWIND $batch AS match
                    MATCH (e:Entity {name: match[3]})
                    MERGE (f:Field {type: match[0], content: match[1]})
                    MERGE (f)-[:REFERENCES {similarity: match[4]}]->(e)
                """, batch=batch)
            processed_matches = i + BATCH_SIZE
            save_update_checkpoint({"processed_matches": processed_matches, "processed_new_entries": processed_new_entries})

        # Create new entities
        for i in tqdm(range(processed_new_entries, len(new_entries), BATCH_SIZE), desc="Adding new entities"):
            batch = new_entries[i:i+BATCH_SIZE]
            if batch:  # Only process if batch is not empty
                try:
                    # Process each entry in the batch
                    for entry in batch:
                        field_type, content = entry[:2]
                        entity_name = " ".join(content.split()[:5])  # Use first 5 words as entity name
                        embedding = get_embedding(content).tolist()
                        
                        session.run("""
                            MERGE (e:Entity {name: $entity_name})
                            ON CREATE SET e.embedding_vector = $embedding
                            MERGE (f:Field {type: $field_type, content: $content})
                            MERGE (f)-[:REFERENCES]->(e)
                        """, entity_name=entity_name, embedding=embedding, field_type=field_type, content=content)
                        
                except Exception as e:
                    logging.error(f"Error processing batch starting at index {i}. Error: {str(e)}")
                    logging.error(f"Problematic entry: {entry}")
                    continue  # Skip this entry and continue with the next one
            processed_new_entries = i + BATCH_SIZE
            save_update_checkpoint({"processed_matches": processed_matches, "processed_new_entries": processed_new_entries})

def load_main_checkpoint():
    if os.path.exists(MAIN_CHECKPOINT_FILE):
        with open(MAIN_CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def save_main_checkpoint(data):
    with open(MAIN_CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_upload_checkpoint():
    if os.path.exists(UPLOAD_CHECKPOINT_FILE):
        with open(UPLOAD_CHECKPOINT_FILE, 'r') as f:
            checkpoint = json.load(f)
        if isinstance(checkpoint, dict) and "processed_files" in checkpoint:
            return checkpoint
    return {"processed_files": [], "current_file": None, "current_batch": 0}

def save_upload_checkpoint(checkpoint_data):
    with open(UPLOAD_CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint_data, f)

def load_similarity_checkpoint():
    if os.path.exists(SIMILARITY_CHECKPOINT_FILE):
        with open(SIMILARITY_CHECKPOINT_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def save_similarity_checkpoint(data):
    with open(SIMILARITY_CHECKPOINT_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_update_checkpoint():
    if os.path.exists(UPDATE_CHECKPOINT_FILE):
        with open(UPDATE_CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"processed_matches": 0, "processed_new_entries": 0}

def save_update_checkpoint(checkpoint_data):
    with open(UPDATE_CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint_data, f)

import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def flatten_provision_content(content):
    if isinstance(content, list):
        return ' '.join(content)
    elif isinstance(content, str):
        return content
    else:
        return str(content)

def flatten_definition_content(definition):
    if isinstance(definition, dict):
        return f"{definition.get('term', '')}: {definition.get('definition', '')}"
    elif isinstance(definition, str):
        return definition
    else:
        return str(definition)

def clean_chapter_number(chapter_number):
    # Remove any non-alphanumeric characters from the end of the string
    return re.sub(r'[^a-zA-Z0-9]+$', '', chapter_number.strip())

def flatten_chapter(chapter):
    flattened_chapter = chapter.copy()
    
    # Clean the chapter number
    flattened_chapter['chapter_number'] = clean_chapter_number(chapter['chapter_number'])
    
    # Flatten substantive provisions
    flattened_chapter['substantive_provisions'] = []
    for provision in chapter.get('substantive_provisions', []):
        flattened_provision = provision.copy()
        flattened_provision['substantive_provisions_text'] = flatten_provision_content(provision.get('substantive_provisions_text', ''))
        flattened_chapter['substantive_provisions'].append(flattened_provision)
    
    # Flatten definitions
    flattened_chapter['definitions'] = []
    for definition in chapter.get('definitions', []):
        flattened_definition = definition.copy()
        flattened_definition['definitions_text'] = flatten_definition_content(definition.get('definitions_text', ''))
        flattened_chapter['definitions'].append(flattened_definition)
    
    return flattened_chapter

def upload_json_to_neo4j(driver, json_folder, batch_size=1):
    checkpoint = load_upload_checkpoint()
    processed_files = set(checkpoint.get("processed_files", []))
    current_file = checkpoint.get("current_file")
    current_batch = checkpoint.get("current_batch", 0)
    
    with open('skipped_provisions.log', 'w') as log_file:
        with driver.session() as session:
            # Create or merge the LegalCode node for the entire United States Code
            session.run("""
                MERGE (usc:LegalCode {doc_number: 'USC'})
                SET usc.name = 'United States Code',
                    usc.jurisdiction = 'United States',
                    usc.government_level = 'Federal'
            """)
            
            file_list = [f for f in os.listdir(json_folder) if f.endswith('.json')]
            for filename in tqdm(file_list):
                if filename in processed_files:
                    logging.info(f"Skipping already processed file: {filename}")
                    continue
                
                if current_file and filename != current_file:
                    continue
                
                logging.info(f"Processing file: {filename}")
                file_path = os.path.join(json_folder, filename)
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Create Title node
                session.run("""
                    MATCH (usc:LegalCode {doc_number: 'USC'})
                    MERGE (t:Title {title_number: $doc_number})
                    SET t.name = $full_title,
                        t.title = $title,
                        t.type = $type,
                        t.jurisdiction = "United States",
                        t.government_level = "Federal",
                        t.effective_date = $enactment_date
                    MERGE (usc)-[:CONTAINS]->(t)
                """, data)
                
                chapters = data['chapters']
                for i in range(current_batch, len(chapters), batch_size):
                    batch = chapters[i:i+batch_size]
                    logging.info(f"Processing batch {i//batch_size + 1} of {len(chapters)//batch_size + 1}")
                    
                    # Preprocess the batch to flatten the structure and clean chapter numbers
                    flattened_batch = []
                    for chapter in batch:
                        try:
                            flattened_chapter = flatten_chapter(chapter)
                            flattened_batch.append(flattened_chapter)
                        except Exception as e:
                            logging.error(f"Error flattening chapter in file {filename}, chapter number {chapter.get('chapter_number', 'unknown')}: {str(e)}")
                            logging.error(f"Problematic chapter data: {json.dumps(chapter, indent=2)}")
                            continue  # Skip this chapter and continue with the next one
                    
                    try:
                        session.run("""
                            MATCH (t:Title {title_number: $doc_number})
                            UNWIND $chapters as chapter
                            MERGE (c:Chapter {
                                title_number: $doc_number,
                                chapter_number: chapter.chapter_number
                            })
                            SET c.chapter_title = chapter.chapter_title,
                                c.label = chapter.chapter_title
                            MERGE (t)-[:CONTAINS]->(c)
                            
                            FOREACH (scope IN chapter.scope |
                                MERGE (s:Scope {
                                    title_number: $doc_number,
                                    chapter_number: chapter.chapter_number,
                                    content: scope.scope_text
                                })
                                SET s.section_number = CASE WHEN scope.section_number IS NOT NULL THEN scope.section_number ELSE '' END,
                                    s.section_title = CASE WHEN scope.section_title IS NOT NULL THEN scope.section_title ELSE '' END,
                                    s.label = CASE 
                                        WHEN size(scope.scope_text) <= 50 THEN scope.scope_text
                                        ELSE left(scope.scope_text, 47) + '...'
                                    END + ' [' + CASE WHEN scope.section_number IS NOT NULL THEN scope.section_number ELSE '' END + ']'
                                MERGE (c)-[:CONTAINS]->(s)
                            )
                            
                            FOREACH (def IN chapter.definitions |
                                MERGE (d:Definition {
                                    title_number: $doc_number,
                                    chapter_number: chapter.chapter_number,
                                    content: def.definitions_text
                                })
                                SET d.section_number = CASE WHEN def.section_number IS NOT NULL THEN def.section_number ELSE '' END,
                                    d.section_title = CASE WHEN def.section_title IS NOT NULL THEN def.section_title ELSE '' END,
                                    d.label = CASE 
                                        WHEN size(def.definitions_text) <= 50 THEN def.definitions_text
                                        ELSE left(def.definitions_text, 47) + '...'
                                    END + ' [' + CASE WHEN def.section_number IS NOT NULL THEN def.section_number ELSE '' END + ']'
                                MERGE (c)-[:CONTAINS]->(d)
                            )
                            
                            FOREACH (provision IN chapter.substantive_provisions |
                                MERGE (p:Provision {
                                    title_number: $doc_number,
                                    chapter_number: chapter.chapter_number,
                                    content: provision.substantive_provisions_text
                                })
                                SET p.section_number = CASE WHEN provision.section_number IS NOT NULL THEN provision.section_number ELSE '' END,
                                    p.section_title = CASE WHEN provision.section_title IS NOT NULL THEN provision.section_title ELSE '' END,
                                    p.label = CASE 
                                        WHEN size(provision.substantive_provisions_text) <= 50 THEN provision.substantive_provisions_text
                                        ELSE left(provision.substantive_provisions_text, 47) + '...'
                                    END + ' [' + CASE WHEN provision.section_number IS NOT NULL THEN provision.section_number ELSE '' END + ']'
                                MERGE (c)-[:CONTAINS]->(p)
                            )
                            
                            FOREACH (condition IN chapter.conditions |
                                MERGE (co:Condition {
                                    title_number: $doc_number,
                                    chapter_number: chapter.chapter_number,
                                    content: condition.conditions_text
                                })
                                SET co.section_number = CASE WHEN condition.section_number IS NOT NULL THEN condition.section_number ELSE '' END,
                                    co.section_title = CASE WHEN condition.section_title IS NOT NULL THEN condition.section_title ELSE '' END,
                                    co.label = CASE 
                                        WHEN size(condition.conditions_text) <= 50 THEN condition.conditions_text
                                        ELSE left(condition.conditions_text, 47) + '...'
                                    END + ' [' + CASE WHEN condition.section_number IS NOT NULL THEN condition.section_number ELSE '' END + ']'
                                MERGE (c)-[:CONTAINS]->(co)
                            )
                            
                            FOREACH (consequence IN chapter.consequences |
                                MERGE (cn:Consequence {
                                    title_number: $doc_number,
                                    chapter_number: chapter.chapter_number,
                                    content: consequence.consequences_text
                                })
                                SET cn.section_number = CASE WHEN consequence.section_number IS NOT NULL THEN consequence.section_number ELSE '' END,
                                    cn.section_title = CASE WHEN consequence.section_title IS NOT NULL THEN consequence.section_title ELSE '' END,
                                    cn.label = CASE 
                                        WHEN size(consequence.consequences_text) <= 50 THEN consequence.consequences_text
                                        ELSE left(consequence.consequences_text, 47) + '...'
                                    END + ' [' + CASE WHEN consequence.section_number IS NOT NULL THEN consequence.section_number ELSE '' END + ']'
                                MERGE (c)-[:CONTAINS]->(cn)
                            )
                        """, {'doc_number': data['doc_number'], 'chapters': flattened_batch})
                    except Exception as e:
                        logging.error(f"Error processing batch in file {filename}, batch starting at index {i}: {str(e)}")
                        logging.error(f"Problematic batch data: {json.dumps(flattened_batch, indent=2)}")
                        save_upload_checkpoint({
                            "processed_files": list(processed_files),
                            "current_file": filename,
                            "current_batch": i
                        })
                        return processed_files, False
                    
                    save_upload_checkpoint({
                        "processed_files": list(processed_files),
                        "current_file": filename,
                        "current_batch": i + batch_size
                    })
                
                processed_files.add(filename)
                save_upload_checkpoint({
                    "processed_files": list(processed_files),
                    "current_file": None,
                    "current_batch": 0
                })
                logging.info(f"Completed processing file: {filename}")
                current_file = None
                current_batch = 0

    return processed_files, True

def create_similarity_relationships(driver, processed_files, batch_size=100):
    main_checkpoint = load_main_checkpoint()
    if main_checkpoint:
        matches, new_entries, processed_docs, review_completed = main_checkpoint
    else:
        matches, new_entries, processed_docs, review_completed = [], [], set(), False

    # Load local embeddings
    local_embeddings, id_to_name, embedding_to_name = load_local_embeddings()
    if not local_embeddings:
        logging.error("No local embeddings loaded. Aborting similarity relationship creation.")
        return [], []

    docs_to_process = processed_files - processed_docs
    logging.info(f"Processing {len(docs_to_process)} documents for similarity relationships")

    for doc_number in tqdm(docs_to_process):
        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (t:Title {title_number: $doc_number})-[:CONTAINS]->(c:Chapter)
                    OPTIONAL MATCH (c)-[:CONTAINS]->(s:Scope)
                    OPTIONAL MATCH (c)-[:CONTAINS]->(d:Definition)
                    RETURN t, collect(distinct c) as chapters, collect(distinct s) as scopes, collect(distinct d) as definitions
                """, doc_number=doc_number)
                
                for record in result:
                    title = record['t']
                    chapters = record['chapters']
                    scopes = record['scopes']
                    definitions = record['definitions']

                    logging.info(f"Processing document {doc_number}: {len(scopes)} scopes, {len(definitions)} definitions")

                    # Process scopes
                    for scope in scopes:
                        process_node_for_similarity(scope, 'Scope', matches, new_entries, local_embeddings, id_to_name)

                    # Process definitions
                    for definition in definitions:
                        process_node_for_similarity(definition, 'Definition', matches, new_entries, local_embeddings, id_to_name)

            processed_docs.add(doc_number)

            if len(processed_docs) % 10 == 0:
                save_main_checkpoint((matches, new_entries, processed_docs, review_completed))
                logging.info(f"Checkpoint saved. Processed {len(processed_docs)} documents so far.")

        except Exception as e:
            logging.error(f"Error processing document {doc_number}: {e}")

    logging.info(f"Similarity relationship processing complete. {len(matches)} matches found, {len(new_entries)} new entries created.")
    return matches, new_entries

def process_node_for_similarity(node, node_type, matches, new_entries, local_embeddings, id_to_name):
    content = node['content']
    embedding = get_embedding(content)
    match, similarity = find_best_match(embedding, local_embeddings, id_to_name)
    
    if match:
        matches.append((node_type, content, 'Entity', match, similarity))
    else:
        new_entries.append((node_type, content))

def find_best_match(embedding, local_embeddings, id_to_name, threshold=0.5):
    similarities = cosine_similarity([embedding], list(local_embeddings.values()))[0]
    best_match_index = np.argmax(similarities)
    if similarities[best_match_index] > threshold:
        best_match_id = list(local_embeddings.keys())[best_match_index]
        return id_to_name.get(best_match_id, best_match_id), similarities[best_match_index]
    return None, 0

def verify_connection(driver):
    try:
        with driver.session() as session:
            result = session.run("RETURN 1")
            result.single()[0]
        logging.info("Successfully connected to Neo4j database")
        return True
    except Exception as e:
        logging.error(f"Failed to connect to Neo4j database: {str(e)}")
        return False

def main():
    driver = None
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        if not verify_connection(driver):
            return

        logging.info("Phase 1: Uploading JSON data to Neo4j")
        processed_files, upload_completed = upload_json_to_neo4j(driver, 'constitution/json/', batch_size=1)
        
        if not upload_completed:
            logging.error("Upload process did not complete successfully. Exiting.")
            return

        logging.info("Phase 2: Creating relationships based on embedding similarities")
        matches, approved_entries = create_similarity_relationships(driver, processed_files)
        
        logging.info("Phase 3: Updating graph with new relationships")
        legal_structure = {
            "legal_code": {
                "name": "United States Code",
                "jurisdiction": "United States",
                "government_level": "Federal",
                "doc_number": "USC"
            },
            "chapters": []  # We don't need to populate this for updating relationships
        }
        update_graph(driver, matches, approved_entries, legal_structure)
        
        logging.info("Process completed successfully")
    except (ServiceUnavailable, SessionExpired) as e:
        logging.error(f"Neo4j database error: {str(e)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
    finally:
        if driver:
            try:
                driver.close()
                logging.info("Neo4j connection closed successfully")
            except Exception as e:
                logging.error(f"Error closing Neo4j connection: {str(e)}")

if __name__ == "__main__":
    main()