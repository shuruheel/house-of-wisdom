import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jReciprocalRelationshipCleaner:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clean_reciprocal_relationships(self):
        with self.driver.session() as session:
            # Get all relationship types
            rel_types = self._get_relationship_types(session)
            
            for rel_type in rel_types:
                self._clean_reciprocal_for_type(session, rel_type)

    def _get_relationship_types(self, session):
        query = "CALL db.relationshipTypes()"
        result = session.run(query)
        return [record["relationshipType"] for record in result]

    def _clean_reciprocal_for_type(self, session, rel_type):
        query = f"""
        MATCH (a)-[r1:{rel_type}]->(b)
        MATCH (b)-[r2:{rel_type}]->(a)
        WHERE id(r1) < id(r2)
        WITH r1, r2
        LIMIT 1000
        DELETE r2
        RETURN count(r2) as removed_count
        """
        
        total_removed = 0
        while True:
            result = session.run(query)
            removed_count = result.single()["removed_count"]
            if removed_count == 0:
                break
            total_removed += removed_count
            logger.info(f"Removed {removed_count} reciprocal relationships of type {rel_type}")
        
        logger.info(f"Finished cleaning reciprocal relationships for {rel_type}. Total removed: {total_removed}")

if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()

    # Get Neo4j connection details from environment variables
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is not set")

    cleaner = Neo4jReciprocalRelationshipCleaner(uri, user, password)
    
    try:
        cleaner.clean_reciprocal_relationships()
    finally:
        cleaner.close()

logger.info("Reciprocal relationship cleaning completed.")