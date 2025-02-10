import os
import re
from neo4j import GraphDatabase
import markdown
from bs4 import BeautifulSoup
from roman import fromRoman
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Neo4j connection setup
uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD")
database = os.getenv("NEO4J_DATABASE", "god")  # Add this line

if not password:
    raise ValueError("NEO4J_PASSWORD environment variable is not set")

driver = GraphDatabase.driver(uri, auth=(user, password))

def clean_text(text):
    return ' '.join(BeautifulSoup(markdown.markdown(text), "html.parser").stripped_strings)

def create_constitution_node(tx):
    tx.run("""
        MERGE (c:LegalCode:Constitution {name: 'United States Constitution'})
        SET c.type = 'Constitution',
            c.jurisdiction = 'United States',
            c.government_level = 'Federal'
    """)

def create_article_node(tx, article_number, title, content):
    tx.run("""
        MATCH (c:Constitution {name: 'United States Constitution'})
        MERGE (a:Article {article_number: $number})
        SET a.title = $title,
            a.content = $content
        MERGE (c)-[:HAS_ARTICLE]->(a)
    """, number=article_number, title=title, content=content)

def create_section_node(tx, article_number, section_number, content):
    tx.run("""
        MATCH (a:Article {article_number: $article_number})
        MERGE (s:Section {section_number: $section_number, article_number: $article_number})
        SET s.content = $content
        MERGE (a)-[:HAS_SECTION]->(s)
    """, article_number=article_number, section_number=section_number, content=content)

def create_subsection_node(tx, article_number, section_number, subsection_number, content):
    tx.run("""
        MATCH (s:Section {number: $section_number})<-[:HAS_SECTION]-(a:Article {number: $article_number})
        MERGE (ss:Subsection {number: $subsection_number, content: $content})
        MERGE (s)-[:HAS_SUBSECTION]->(ss)
    """, article_number=article_number, section_number=section_number, subsection_number=subsection_number, content=content)

def create_bill_of_rights_node(tx):
    tx.run("""
        MATCH (c:Constitution {name: 'United States Constitution'})
        MERGE (b:BillOfRights {name: 'Bill of Rights'})
        MERGE (c)-[:HAS_BILL_OF_RIGHTS]->(b)
    """)

def create_amendment_node(tx, amendment_number, title, content, is_bill_of_rights=False):
    query = """
        MATCH (c:Constitution {name: 'United States Constitution'})
        MERGE (a:Amendment {amendment_number: $number, title: $title, content: $content})
        MERGE (c)-[:HAS_AMENDMENT]->(a)
    """
    if is_bill_of_rights:
        query += """
        WITH a
        MATCH (b:BillOfRights {name: 'Bill of Rights'})
        MERGE (b)-[:INCLUDES_AMENDMENT]->(a)
        """
    tx.run(query, number=amendment_number, title=title, content=content)

def create_amendment_section_node(tx, amendment_number, section_number, content):
    tx.run("""
        MATCH (a:Amendment {amendment_number: $amendment_number})
        MERGE (s:Section {section_number: $section_number, amendment_number: $amendment_number})
        SET s.content = $content
        MERGE (a)-[:HAS_SECTION]->(s)
    """, amendment_number=amendment_number, section_number=section_number, content=content)

def parse_main_constitution(file_path, dry_run=False):
    with open(file_path, 'r') as file:
        content = file.read()
    
    articles = re.split(r'## Article\. [IVX]+\.', content)[1:]
    
    with driver.session(database=database) as session:  # Update this line
        if dry_run:
            logging.info("Dry run: Would create Constitution node")
        else:
            create_constitution_node(session)
        
        for i, article in enumerate(articles, 1):
            article_title = f"Article {i}"
            article_content = clean_text(article)
            if dry_run:
                logging.info(f"Dry run: Would create/update Article node: {article_title}")
            else:
                create_article_node(session, i, article_title, article_content)
            
            sections = re.split(r'### Section\. \d+\.', article)
            for j, section in enumerate(sections[1:], 1):
                section_content = clean_text(section)
                if dry_run:
                    logging.info(f"Dry run: Would create/update Section node: Article {i}, Section {j}")
                else:
                    create_section_node(session, i, j, section_content)
                
                subsections = re.split(r'#### SubSection\. \d+\.', section)
                for k, subsection in enumerate(subsections[1:], 1):
                    subsection_content = clean_text(subsection)
                    if dry_run:
                        logging.info(f"Dry run: Would create/update Subsection node: Article {i}, Section {j}, Subsection {k}")
                    else:
                        create_subsection_node(session, i, j, k, subsection_content)

def parse_bill_of_rights(file_path, dry_run=False):
    with open(file_path, 'r') as file:
        content = file.read()
    
    amendments = re.split(r'## Amendment [IVX]+\.', content)[1:]
    
    with driver.session(database=database) as session:  # Update this line
        if dry_run:
            logging.info("Dry run: Would create Bill of Rights node")
        else:
            create_bill_of_rights_node(session)
        for i, amendment in enumerate(amendments, 1):
            amendment_title = f"Amendment {i}"
            amendment_content = clean_text(amendment)
            if dry_run:
                logging.info(f"Dry run: Would create Amendment node: {amendment_title} (Bill of Rights)")
            else:
                create_amendment_node(session, i, amendment_title, amendment_content, is_bill_of_rights=True)

def parse_amendments(folder_path, dry_run=False):
    with driver.session(database=database) as session:  # Update this line
        for filename in sorted(os.listdir(folder_path)):
            if filename.endswith('.md'):
                with open(os.path.join(folder_path, filename), 'r') as file:
                    content = file.read()
                    
                    match = re.search(r'## Amendment ([IVXLCDM]+)\.', content)
                    if match:
                        amendment_number = fromRoman(match.group(1))
                        amendment_content = content.split('\n\n', 2)[-1]
                        
                        if amendment_number <= 10:
                            continue
                        
                        amendment_title = f"Amendment {amendment_number}"
                        amendment_content = clean_text(amendment_content)
                        if dry_run:
                            logging.info(f"Dry run: Would create Amendment node: {amendment_title}")
                        else:
                            create_amendment_node(session, amendment_number, amendment_title, amendment_content, is_bill_of_rights=False)
                        
                        # Parse sections within the amendment
                        sections = re.split(r'### Section\. \d+\.', amendment_content)
                        for j, section in enumerate(sections[1:], 1):
                            section_content = clean_text(section)
                            if dry_run:
                                logging.info(f"Dry run: Would create/update Section node: Amendment {amendment_number}, Section {j}")
                            else:
                                create_amendment_section_node(session, amendment_number, j, section_content)
                    else:
                        logging.warning(f"Could not parse amendment number from file {filename}")

def main(dry_run=False):
    constitution_path = 'USA-Constitution/Constitution.md'
    bill_of_rights_path = 'USA-Constitution/BillOfRights.md'
    amendments_folder = 'USA-Constitution/amendments'

    if dry_run:
        logging.info("Performing dry run...")
    else:
        logging.info("Starting Constitution integration...")
    
    try:
        parse_main_constitution(constitution_path, dry_run)
        parse_bill_of_rights(bill_of_rights_path, dry_run)
        parse_amendments(amendments_folder, dry_run)

        if dry_run:
            logging.info("Dry run completed successfully. No changes were made to the database.")
        else:
            logging.info("US Constitution has been successfully added to the graph database.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
    finally:
        driver.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Upload US Constitution to Neo4j database")
    parser.add_argument('--dry-run', action='store_true', help="Perform a dry run without making changes to the database")
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)