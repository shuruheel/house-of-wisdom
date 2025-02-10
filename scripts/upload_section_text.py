import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm
import logging
import sys
import re

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE", "god")  # Default to "neo4j" if not specified

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_chapter_number(chapter_number):
    # Replace non-breaking spaces with regular spaces
    chapter_number = chapter_number.replace('\xa0', ' ')
    # Remove trailing dash, em dash, and trim
    return chapter_number.rstrip('—').strip()

def should_exclude_section(section_title):
    exclude_words = ["Omitted", "Repealed", "Transferred"]
    return any(word in section_title for word in exclude_words)

def clean_section_number(section_number):
    # Remove leading and trailing quotation marks
    section_number = section_number.strip('“')
    # Replace non-breaking spaces with regular spaces
    section_number = section_number.replace('\xa0', ' ')
    # Remove trailing period if present
    section_number = section_number.rstrip('—')
    # Remove trailing dash or em dash if present
    section_number = section_number.rstrip('.')
    return section_number

def process_json_file(file_path, session):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        title_number = data['metadata']['doc_number']
        
        for chapter in data['chapters']:
            chapter_number = clean_chapter_number(chapter['chapter_number'])
            
            for section in chapter['sections']:
                if should_exclude_section(section['section_title']):
                    continue
                
                clean_section_num = clean_section_number(section['section_number'])
                
                result = session.run("""
                    // Match Chapter node (now mandatory)
                    MATCH (c:Chapter {title_number: $title_number, chapter_number: $chapter_number})
                    
                    // Create or update Section node
                    MERGE (s:Section {
                        title_number: $title_number,
                        chapter_number: $chapter_number,
                        section_number: $section_number
                    })
                    SET s.content = $section_text,
                        s.section_title = $section_title
                    
                    // Create CONTAINS relationship from Chapter to Section
                    MERGE (c)-[:CONTAINS]->(s)
                    
                    // Match Provision node if exists
                    WITH s
                    OPTIONAL MATCH (p:Provision {
                        title_number: s.title_number,
                        chapter_number: s.chapter_number,
                        section_number: s.section_number
                    })
                    
                    // Create CONTAINS relationship from Section to Provision if found
                    FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (s)-[:CONTAINS]->(p)
                    )
                    RETURN count(s) as section_count
                """, {
                    'title_number': title_number,
                    'chapter_number': chapter_number,
                    'section_number': clean_section_num,
                    'section_title': section['section_title'],
                    'section_text': section['section_text']
                })
                
                section_count = result.single()['section_count']
                if section_count == 0:
                    logging.warning(f"No Section created for {title_number} - {chapter_number} - {clean_section_num}")
                else:
                    logging.debug(f"Section created: {title_number} - {chapter_number} - {clean_section_num}")
    
    except Exception as e:
        logging.error(f"Error processing file {file_path}: {str(e)}")
        raise

def main():
    json_folder = 'output_json'
    
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session(database=neo4j_database) as session:
            for filename in tqdm(os.listdir(json_folder)):
                if filename.endswith('.json'):
                    file_path = os.path.join(json_folder, filename)
                    logging.info(f"Processing file: {filename}")
                    with session.begin_transaction() as tx:
                        process_json_file(file_path, tx)
                        tx.commit()
            
            # Check the total number of Section nodes after processing
            check_result = session.run("MATCH (s:Section) RETURN count(s) as section_count")
            total_sections = check_result.single()['section_count']
            logging.info(f"Total Section nodes after processing: {total_sections}")
        
        logging.info("All files processed successfully")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    main()