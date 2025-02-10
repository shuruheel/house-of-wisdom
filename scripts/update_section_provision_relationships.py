import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging
import re

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")
neo4j_database = os.getenv("NEO4J_DATABASE", "god")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_numeric(text):
    return ''.join(filter(str.isdigit, text))

def match_provisions_to_sections(tx):
    # Fetch all Provisions and Sections
    result = tx.run("""
        MATCH (p:Provision)
        OPTIONAL MATCH (s:Section)
        WHERE s.title_number = p.title_number AND s.chapter_number = p.chapter_number
        RETURN p.title_number AS title, p.chapter_number AS chapter, p.section_number AS p_section,
               s.section_number AS s_section, id(p) AS p_id, id(s) AS s_id
    """)
    
    matches = []
    for record in result:
        p_id = record['p_id']
        s_id = record['s_id']
        if s_id is not None:
            p_section_num = extract_numeric(record['p_section'])
            s_section_num = extract_numeric(record['s_section'])
            if p_section_num == s_section_num:
                matches.append((p_id, s_id))
        
    # Create relationships for matches
    for p_id, s_id in matches:
        tx.run("""
            MATCH (p:Provision), (s:Section)
            WHERE id(p) = $p_id AND id(s) = $s_id
            MERGE (s)-[:CONTAINS]->(p)
        """, p_id=p_id, s_id=s_id)
    
    return len(matches)

def main():
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session(database=neo4j_database) as session:
            # Match Provisions to Sections
            match_count = session.write_transaction(match_provisions_to_sections)
            logging.info(f"Created {match_count} relationships between Sections and Provisions")
            
            # Check unmatched Provisions
            unmatched_count = session.run("""
                MATCH (p:Provision)
                WHERE NOT (p)<-[:CONTAINS]-(:Section)
                RETURN count(p) AS count
            """).single()['count']
            logging.info(f"Unmatched Provisions: {unmatched_count}")
            
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise
    finally:
        if 'driver' in locals():
            driver.close()

if __name__ == "__main__":
    main()