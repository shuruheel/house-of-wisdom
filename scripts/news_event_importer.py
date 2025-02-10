import os
import json
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from tqdm import tqdm
import glob

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewsEventImporter:
    def __init__(self, batch_size=500):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.batch_size = batch_size

    def close(self):
        self.driver.close()

    def import_news_events(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            with self.driver.session() as session:
                self._import_entities(session, data.get('entities', []))
                self._import_concepts(session, data.get('concepts', []))
                self._import_events(session, data.get('events', []))
                self._import_stories(session, data.get('stories', []))
                self._import_concept_relationships(session, data.get('concept_relationships', []))

            logger.info("News events import completed successfully.")
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {file_path}")
        except ServiceUnavailable:
            logger.error("Neo4j database is unavailable. Please check your connection.")
        except SessionExpired:
            logger.error("Neo4j session has expired. Please try again.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

    def _batch_import(self, session, data, import_query, data_type):
        total_batches = (len(data) + self.batch_size - 1) // self.batch_size
        total_nodes_created = 0
        total_relationships_created = 0
        
        with tqdm(total=total_batches, desc=f"Importing {data_type}", disable=True) as pbar:
            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                try:
                    result = session.run(import_query, batch=batch)
                    summary = result.consume()
                    total_nodes_created += summary.counters.nodes_created
                    total_relationships_created += summary.counters.relationships_created
                    pbar.update(1)
                except Exception as e:
                    logger.error(f"Error importing {data_type} batch {i // self.batch_size + 1}: {str(e)}")
                    pbar.update(1)

        logger.info(f"{data_type} import completed. Nodes created: {total_nodes_created}, Relationships created: {total_relationships_created}")

    def _import_entities(self, session, entities):
        logger.info(f"Importing {len(entities)} entities")
        query = """
        UNWIND $batch AS entity
        MERGE (e:Entity {name: entity.name})
        ON CREATE SET e.type = entity.type, e.description = entity.description
        ON MATCH SET e.type = entity.type, e.description = entity.description
        """
        self._batch_import(session, entities, query, "Entities")

    def _import_concepts(self, session, concepts):
        logger.info(f"Importing {len(concepts)} concepts")
        query = """
        UNWIND $batch AS concept
        MERGE (c:Concept {name: concept.name})
        ON CREATE SET c.description = concept.description
        ON MATCH SET c.description = concept.description
        """
        self._batch_import(session, concepts, query, "Concepts")

    def _import_events(self, session, events):
        logger.info(f"Importing {len(events)} events")
        query = """
        UNWIND $batch AS event
        MERGE (e:Event {name: event.name})
        SET 
            e.description = event.description,
            e.start_date = event.start_date,
            e.end_date = event.end_date,
            e.date_precision = event.date_precision,
            e.emotion = event.emotion,
            e.emotion_intensity = event.emotion_intensity,
            e.next_event = event.next_event
        WITH e, event
        UNWIND event.involved_entities AS entity_name
        MATCH (entity:Entity {name: entity_name})
        MERGE (e)-[:INVOLVES]->(entity)
        WITH e, event
        UNWIND event.related_concepts AS concept_name
        MATCH (concept:Concept {name: concept_name})
        MERGE (e)-[:RELATES_TO]->(concept)
        """
        self._batch_import(session, events, query, "Events")

    def _import_stories(self, session, stories):
        logger.info(f"Importing {len(stories)} stories")
        query = """
        UNWIND $batch AS story
        MERGE (s:Story {name: story.name})
        ON CREATE SET s.description = story.description
        ON MATCH SET s.description = story.description
        With s, story
        UNWIND story.events AS event_name
        MATCH (event:Event {name: event_name})
        MERGE (s)-[:INCLUDES]->(event)
        """
        self._batch_import(session, stories, query, "Stories")

    def _import_concept_relationships(self, session, concept_relationships):
        logger.info(f"Importing {len(concept_relationships)} concept relationships")
        query = """
        UNWIND $batch AS rel
        MATCH (c1:Concept {name: rel.from})
        MATCH (c2:Concept {name: rel.to})
        MERGE (c1)-[r:RELATED_TO {type: rel.type}]->(c2)
        SET r.strength = rel.strength, 
            r.description = rel.description
        """
        self._batch_import(session, concept_relationships, query, "Concept Relationships")

    def import_checkpoint_files(self, checkpoint_folder):
        logger.info(f"Importing checkpoint files from {checkpoint_folder}")
        checkpoint_files = glob.glob(f"{checkpoint_folder}/*_2024*.json")
        
        for file_path in checkpoint_files:
            logger.info(f"Processing checkpoint file: {file_path}")
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                with self.driver.session() as session:
                    self._import_entities(session, data.get('entities', []))
                    self._import_concepts(session, data.get('concepts', []))
                    self._import_events(session, data.get('events', []))
                    self._import_stories(session, data.get('stories', []))
                    self._import_concept_relationships(session, data.get('concept_relationships', []))

                logger.info(f"Successfully imported data from {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)

if __name__ == "__main__":
    importer = NewsEventImporter()
    try:
        importer.import_news_events("news_events/merged_news_events.json")
    finally:
        importer.close()