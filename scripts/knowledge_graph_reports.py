import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
import numpy as np
from gensim.models import Word2Vec
import multiprocessing
from sentence_transformers import SentenceTransformer
import logging
import dateutil.parser
from datetime import datetime, date
import time
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
from neo4j import time

def parse_date(date_string):
    if not date_string or date_string.lower() in ['n/a', 'unknown', '', 'yyyy-mm-dd']:
        return None
    try:
        parsed_date = dateutil.parser.parse(date_string, default=datetime(1, 1, 1))
        return parsed_date.date()  # Return a date object
    except:
        return None

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeGraphEnhancer:
    def __init__(self, skip_embeddings=True):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.graph = None
        self.embeddings = None
        self.skip_embeddings = skip_embeddings

    def import_chunk(self, chunk_file, max_retries=3, retry_delay=5):
        with open(chunk_file, 'r') as f:
            data = json.load(f)
        
        # Extract report information from file path
        path_parts = chunk_file.split(os.sep)
        report_name = path_parts[-2]
        chunk_number = int(path_parts[-1].split('_')[1].split('.')[0])
        
        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    self._import_report(session, report_name, chunk_number)
                    self._import_entities(session, data.get('entities', []), report_name)
                    self._import_concepts(session, data.get('concepts', []), report_name)
                    self._import_events(session, data.get('events', []), report_name)
                    self._import_stories(session, data.get('stories', []), report_name)
                    self._import_claims(session, data.get('claims', []), report_name)
                    self._import_concept_relationships(session, data.get('concept_relationships', []), report_name)
                    self._import_data_points(session, data.get('data_points', []), report_name)
                return  # If successful, exit the function
            except (ServiceUnavailable, SessionExpired) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error processing {chunk_file}: {str(e)}")
                    raise
                else:
                    logger.warning(f"Connection error, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)

    def _import_report(self, session, report_name, chunk_number):
        # Load the summary file
        summary_file = f"data/summaries/{report_name}_summary.json"
        try:
            with open(summary_file, 'r') as f:
                summary_data = json.load(f)
            
            report_title = summary_data['report']['title']
            report_organization = summary_data['report']['organization']
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            logger.warning(f"Could not load or parse summary file for {report_name}")
            report_title = ""
            report_organization = ""

        session.run("""
        MERGE (r:Report {name: $report_name})
        SET r.title = $title,
            r.organization = $organization
        """, report_name=report_name, title=report_title, organization=report_organization)

    def _import_entities(self, session, entities, report_name):
        for entity in entities:
            name = self._to_title_case(entity.get('name', ''))
            session.run("""
            MERGE (e:Entity {name: $name})
            ON CREATE SET e.type = $type, e.description = $description, e.language = $language
            ON MATCH SET e.type = $type, e.description = $description, e.language = $language
            WITH e
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(e)
            """, name=name, type=entity.get('type', ''), 
                description=entity.get('description', ''), language=entity.get('language', ''),
                report_name=report_name)
            
            for related in entity.get('related_entities', []):
                if isinstance(related, dict) and self._validate_relationship(entity, related):
                    rel_type = self._sanitize_relationship_type(related.get('relationship_type', 'RELATED_TO'))
                    related_name = self._to_title_case(related.get('name', ''))
                    session.run(f"""
                    MATCH (e1:Entity {{name: $name1}})
                    MATCH (e2:Entity {{name: $name2}})
                    MERGE (e1)-[r:`{rel_type}`]->(e2)
                    SET r.description = $rel_description
                    WITH e2
                    MATCH (r:Report {{name: $report_name}})
                    MERGE (r)-[:CONTAINS]->(e2)
                    """, name1=name, 
                        name2=related_name, 
                        rel_description=related.get('relationship_description', ''),
                        report_name=report_name)

    def _sanitize_relationship_type(self, rel_type):
        # Replace spaces with underscores and remove any non-alphanumeric characters
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in rel_type.upper().replace(' ', '_'))

    def _validate_relationship(self, entity1, entity2):
        # Existing logic
        if entity1.get('type') == 'Author':
            valid_relations = ['Report', 'Concept', 'Organization']
            if entity2.get('type') not in valid_relations:
                return False
        
        # Prevent circular relationships
        if entity1.get('name') == entity2.get('name'):
            return False
        
        # Limit the number of relationships per entity
        max_relationships = 50  # Adjust this number as needed
        relationship_count = self._get_relationship_count(entity1.get('name'))
        if relationship_count is not None and relationship_count > max_relationships:
            return False
        
        # Prevent certain types of entities from relating to each other
        incompatible_types = [
            ('Country', 'DataPoint'),
            ('Organization', 'Event'),
            # Add more incompatible pairs as needed
        ]
        if (entity1.get('type'), entity2.get('type')) in incompatible_types:
            return False
        
        return True

    def _get_relationship_count(self, entity_name):
        # Implement a method to count the number of relationships for an entity
        # This could involve a database query or maintaining a counter
        # For now, return None to avoid the TypeError
        return None

    def _import_concepts(self, session, concepts, report_name):
        for concept in concepts:
            name = self._to_title_case(concept['name'])
            session.run("""
            MERGE (c:Concept {name: $name})
            ON CREATE SET c.description = $description, c.language = $language
            ON MATCH SET c.description = $description, c.language = $language
            WITH c
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(c)
            """, name=name, description=concept['description'], 
                language=concept.get('language', 'unknown'),  # Use get() with a default value
                report_name=report_name)

    def _import_events(self, session, events, report_name):
        for event in events:
            start_date = parse_date(event.get('start_date'))
            end_date = parse_date(event.get('end_date'))

            # Skip events with start_date in the future
            if start_date and start_date > date.today():
                continue

            name = self._to_title_case(event['name'])
            session.run("""
            MERGE (e:Event {name: $name})
            ON CREATE SET e.description = $description, 
                          e.start_date = $start_date, 
                          e.end_date = $end_date,
                          e.date_precision = $date_precision
            ON MATCH SET e.description = $description, 
                         e.start_date = $start_date, 
                         e.end_date = $end_date,
                         e.date_precision = $date_precision
            WITH e
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(e)
            """, 
            name=name, 
            description=event.get('description', ''),
            start_date=time.Date.from_native(start_date) if start_date else None,
            end_date=time.Date.from_native(end_date) if end_date else None,
            date_precision=event.get('date_precision', ''),
            report_name=report_name)
            
            for entity in event.get('involved_entities', []):
                entity_name = self._to_title_case(entity)
                session.run("""
                MATCH (event:Event {name: $event_name})
                MATCH (entity:Entity {name: $entity_name})
                MERGE (event)-[:INVOLVES]->(entity)
                """, event_name=name, entity_name=entity_name)
            
            for concept in event.get('related_concepts', []):
                concept_name = self._to_title_case(concept)
                session.run("""
                MATCH (event:Event {name: $event_name})
                MATCH (concept:Concept {name: $concept_name})
                MERGE (event)-[:RELATES_TO]->(concept)
                """, event_name=name, concept_name=concept_name)
            
            if event.get('next_event'):
                session.run("""
                MATCH (e1:Event {name: $event_name})
                MATCH (e2:Event {name: $next_event_name})
                MERGE (e1)-[:NEXT]->(e2)
                """, event_name=name, next_event_name=self._to_title_case(event['next_event']))

    def _import_stories(self, session, stories, report_name):
        for story in stories:
            session.run("""
            MERGE (s:Story {name: $name})
            ON CREATE SET s.description = $description, s.version = $version
            ON MATCH SET s.description = $description, s.version = $version
            WITH s
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(s)
            """, name=story['name'], description=story['description'], version=story['version'],
                report_name=report_name)
            
            for event in story['events']:
                session.run("""
                MATCH (story:Story {name: $story_name})
                MATCH (event:Event {name: $event_name})
                MERGE (story)-[:INCLUDES]->(event)
                """, story_name=story['name'], event_name=event)

    def _import_claims(self, session, claims, report_name):
        for claim in claims:
            session.run("""
            MERGE (c:Claim {content: $content})
            ON CREATE SET c.source = $source, c.confidence = $confidence
            ON MATCH SET c.source = $source, c.confidence = $confidence
            WITH c
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(c)
            """, content=claim['content'], source=claim['source'], confidence=claim['confidence'], 
                report_name=report_name)
            
            if 'about_entity' in claim:
                session.run("""
                MATCH (c:Claim {content: $content})
                MATCH (e:Entity {name: $entity_name})
                MERGE (c)-[r:ABOUT]->(e)
                """, content=claim['content'], entity_name=self._to_title_case(claim['about_entity']))
            
            if 'supports_concept' in claim:
                session.run("""
                MATCH (c:Claim {content: $content})
                MATCH (concept:Concept {name: $concept_name})
                MERGE (c)-[r:SUPPORTS]->(concept)
                """, content=claim['content'], concept_name=self._to_title_case(claim['supports_concept']))
            
            for contradicting_claim in claim.get('contradicts', []):
                session.run("""
                MATCH (c1:Claim {content: $content1})
                MERGE (c2:Claim {content: $content2})
                MERGE (c1)-[r:CONTRADICTS]->(c2)
                """, content1=claim['content'], content2=contradicting_claim)

    def _import_concept_relationships(self, session, concept_relationships, report_name):
        for rel in concept_relationships:
            rel_type = self._sanitize_relationship_type(rel['type'])
            from_concept = self._to_title_case(rel['from'])
            to_concept = self._to_title_case(rel['to'])
            session.run(f"""
            MATCH (c1:Concept {{name: $from_}})
            MATCH (c2:Concept {{name: $to}})
            MERGE (c1)-[r:`{rel_type}`]->(c2)
            SET r.strength = $strength, 
                r.context = $context, 
                r.bidirectional = $bidirectional
            WITH c1, c2
            MATCH (r:Report {{name: $report_name}})
            MERGE (r)-[:CONTAINS]->(c1)
            MERGE (r)-[:CONTAINS]->(c2)
            """, from_=from_concept, to=to_concept, strength=rel['strength'], 
                context=rel['context'], bidirectional=rel['bidirectional'],
                report_name=report_name)

    def _import_data_points(self, session, data_points, report_name):
        for data_point in data_points:
            session.run("""
            MERGE (d:DataPoint {name: $name})
            ON CREATE SET d.description = $description, d.value = $value, d.unit = $unit
            ON MATCH SET d.description = $description, d.value = $value, d.unit = $unit
            WITH d
            MATCH (r:Report {name: $report_name})
            MERGE (r)-[:CONTAINS]->(d)
            """, name=data_point['name'], description=data_point['description'], 
                value=data_point['value'], unit=data_point['unit'], report_name=report_name)

    def _to_title_case(self, string):
        return string.title() if string else string

    def generate_embeddings(self, dimensions=64, walk_length=10, num_walks=5, workers=None, max_retries=3, retry_delay=5):
        if self.skip_embeddings:
            logger.info("Skipping embedding generation as requested.")
            return

        if workers is None:
            workers = max(1, multiprocessing.cpu_count() - 1)

        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    # Get all nodes and their relationships
                    result = session.run("""
                    MATCH (n)
                    OPTIONAL MATCH (n)-[r]->(m)
                    RETURN n.uuid AS node_id, collect(m.uuid) AS neighbors
                    """)
                    graph = {record['node_id']: record['neighbors'] for record in result}

                # Generate random walks
                walks = []
                for _ in range(num_walks):
                    for node in graph:
                        walk = [node]
                        for _ in range(walk_length - 1):
                            current = walk[-1]
                            if graph[current]:
                                walk.append(np.random.choice(graph[current]))
                            else:
                                break
                        walks.append([str(node) for node in walk])

                # Train Word2Vec model
                model = Word2Vec(walks, vector_size=dimensions, window=5, min_count=0, 
                                 sg=1, workers=workers, epochs=5)

                # Store embeddings in the database
                embeddings = {node: model.wv[str(node)].tolist() for node in graph}
                
                with self.driver.session() as session:
                    session.run("""
                    UNWIND $embeddings AS emb
                    MATCH (n {uuid: emb.node})
                    SET n.embedding = emb.vector
                    """, embeddings=[{'node': k, 'vector': v} for k, v in embeddings.items()])

                logger.info(f"Generated and stored embeddings for {len(embeddings)} nodes")
                return  # If successful, exit the function
            except (ServiceUnavailable, SessionExpired, TransientError) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate embeddings after {max_retries} attempts: {str(e)}")
                    raise
                else:
                    logger.warning(f"Database unavailable, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)

    def run_enhancement(self):
        try:
            if not self.skip_embeddings:
                self.generate_embeddings()
        except Exception as e:
            logger.error(f"Error during enhancement: {str(e)}", exc_info=True)
            raise

    def close(self):
        if self.driver:
            self.driver.close()

if __name__ == "__main__":
    enhancer = KnowledgeGraphEnhancer(skip_embeddings=True)  # Set to True to skip embedding generation
    try:
        enhancer.run_enhancement()
    finally:
        enhancer.close()