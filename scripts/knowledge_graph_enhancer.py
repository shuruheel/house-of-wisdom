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
from datetime import datetime
import time
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

def parse_date(date_string):
    if not date_string or date_string.lower() in ['n/a', 'unknown', '', 'yyyy-mm-dd']:
        return None
    try:
        parsed_date = dateutil.parser.parse(date_string, default=datetime(1, 1, 1))
        return parsed_date.strftime('%Y-%m-%d')
    except:
        return None

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeGraphEnhancer:
    def __init__(self, skip_embeddings=False):
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
        
        # Extract book and chapter information from file path
        path_parts = chunk_file.split(os.sep)
        book_name = path_parts[-3]
        chapter_number = int(path_parts[-2].split('_')[-1])
        chunk_number = int(path_parts[-1].split('_')[1].split('.')[0])
        
        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    self._import_book_and_chapter(session, book_name, chapter_number, chunk_number)
                    self._import_entities(session, data.get('entities', []), book_name, chapter_number)
                    self._import_concepts(session, data.get('concepts', []), book_name, chapter_number)
                    self._import_events(session, data.get('events', []), book_name, chapter_number)
                    self._import_stories(session, data.get('stories', []), book_name, chapter_number)
                    self._import_claims(session, data.get('claims', []), book_name, chapter_number)
                    self._import_concept_relationships(session, data.get('concept_relationships', []), book_name, chapter_number)
                    self._import_poetry(session, data.get('poetry', []), book_name, chapter_number)
                return  # If successful, exit the function
            except (ServiceUnavailable, SessionExpired) as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error processing {chunk_file}: {str(e)}")
                    raise
                else:
                    logger.warning(f"Connection error, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)

    def _import_book_and_chapter(self, session, book_name, chapter_number, chunk_number):
        session.run("""
        MERGE (b:Book {name: $book_name})
        MERGE (c:Chapter {book: $book_name, number: $chapter_number})
        MERGE (b)-[:CONTAINS]->(c)
        """, book_name=book_name, chapter_number=chapter_number)

    def _import_entities(self, session, entities, book_name, chapter_number):
        for entity in entities:
            session.run("""
            MERGE (e:Entity {name: $name})
            ON CREATE SET e.type = $type, e.description = $description, e.language = $language
            ON MATCH SET e.type = $type, e.description = $description, e.language = $language
            WITH e
            MATCH (b:Book {name: $book_name})
            MATCH (c:Chapter {book: $book_name, number: $chapter_number})
            MERGE (b)-[:CONTAINS]->(e)
            MERGE (c)-[:CONTAINS]->(e)
            """, name=entity.get('name', ''), type=entity.get('type', ''), 
                description=entity.get('description', ''), language=entity.get('language', ''),
                book_name=book_name, chapter_number=chapter_number)
            
            for related in entity.get('related_entities', []):
                if isinstance(related, dict) and self._validate_relationship(entity, related):
                    rel_type = self._sanitize_relationship_type(related.get('relationship_type', 'RELATED_TO'))
                    session.run(f"""
                    MATCH (e1:Entity {{name: $name1}})
                    MATCH (e2:Entity {{name: $name2}})
                    MERGE (e1)-[r:`{rel_type}`]->(e2)
                    SET r.description = $rel_description
                    WITH e2
                    MATCH (b:Book {{name: $book_name}})
                    MATCH (c:Chapter {{book: $book_name, number: $chapter_number}})
                    MERGE (b)-[:CONTAINS]->(e2)
                    MERGE (c)-[:CONTAINS]->(e2)
                    """, name1=entity.get('name', ''), 
                        name2=related.get('name', ''), 
                        rel_description=related.get('relationship_description', ''),
                        book_name=book_name, chapter_number=chapter_number)

    def _sanitize_relationship_type(self, rel_type):
        # Replace spaces with underscores and remove any non-alphanumeric characters
        return ''.join(c if c.isalnum() or c == '_' else '_' for c in rel_type.upper().replace(' ', '_'))

    def _validate_relationship(self, entity1, entity2):
        # Add your validation logic here
        # For example, prevent 'Author' from relating to too many entities
        if entity1.get('type') == 'Author' and entity2.get('type') not in ['Book', 'Article']:
            return False
        return True

    def _import_concepts(self, session, concepts, book_name, chapter_number):
        for concept in concepts:
            # Use a default language if not present
            language = concept.get('language', 'en')  # Default to 'en' for English
            session.run("""
                MERGE (c:Concept {name: $name})
                SET c.description = $description,
                    c.language = $language,
                    c.book_name = $book_name,
                    c.chapter_number = $chapter_number
            """, name=concept['name'], description=concept['description'], language=language,
                 book_name=book_name, chapter_number=chapter_number)

    def _import_events(self, session, events, book_name, chapter_number):
        for event in events:
            start_date = parse_date(event.get('start_date'))
            end_date = parse_date(event.get('end_date'))

            session.run("""
            MERGE (e:Event {name: $name})
            ON CREATE SET e.description = $description, 
                          e.start_date = $start_date, 
                          e.end_date = $end_date,
                          e.date_precision = $date_precision, 
                          e.emotion = $emotion, 
                          e.emotion_intensity = $emotion_intensity
            ON MATCH SET e.description = $description, 
                         e.start_date = $start_date, 
                         e.end_date = $end_date,
                         e.date_precision = $date_precision, 
                         e.emotion = $emotion, 
                         e.emotion_intensity = $emotion_intensity
            WITH e
            MATCH (b:Book {name: $book_name})
            MATCH (ch:Chapter {book: $book_name, number: $chapter_number})
            MERGE (b)-[:CONTAINS]->(e)
            MERGE (ch)-[:CONTAINS]->(e)
            """, 
            name=event['name'], 
            description=event.get('description', ''),
            start_date=start_date,
            end_date=end_date,
            date_precision=event.get('date_precision', ''),
            emotion=event.get('emotion', ''),
            emotion_intensity=event.get('emotion_intensity', 0.0),
            book_name=book_name,
            chapter_number=chapter_number)
            
            for entity in event.get('involved_entities', []):
                session.run("""
                MATCH (event:Event {name: $event_name})
                MATCH (entity:Entity {name: $entity_name})
                MERGE (event)-[:INVOLVES]->(entity)
                """, event_name=event['name'], entity_name=entity)
            
            for concept in event.get('related_concepts', []):
                session.run("""
                MATCH (event:Event {name: $event_name})
                MATCH (concept:Concept {name: $concept_name})
                MERGE (event)-[:RELATES_TO]->(concept)
                """, event_name=event['name'], concept_name=concept)
            
            if event.get('next_event'):
                session.run("""
                MATCH (e1:Event {name: $event_name})
                MATCH (e2:Event {name: $next_event_name})
                MERGE (e1)-[:NEXT]->(e2)
                """, event_name=event['name'], next_event_name=event['next_event'])

    def _import_stories(self, session, stories, book_name, chapter_number):
        for story in stories:
            session.run("""
            MERGE (s:Story {name: $name})
            ON CREATE SET s.description = $description, s.version = $version
            ON MATCH SET s.description = $description, s.version = $version
            WITH s
            MATCH (b:Book {name: $book_name})
            MATCH (ch:Chapter {book: $book_name, number: $chapter_number})
            MERGE (b)-[:CONTAINS]->(s)
            MERGE (ch)-[:CONTAINS]->(s)
            """, name=story['name'], description=story['description'], version=story['version'],
                book_name=book_name, chapter_number=chapter_number)
            
            for event in story['events']:
                session.run("""
                MATCH (story:Story {name: $story_name})
                MATCH (event:Event {name: $event_name})
                MERGE (story)-[:INCLUDES]->(event)
                """, story_name=story['name'], event_name=event)

    def _import_claims(self, session, claims, book_name, chapter_number):
        for claim in claims:
            session.run("""
            MERGE (c:Claim {content: $content})
            ON CREATE SET c.source = $source, c.confidence = $confidence, c.timestamp = $timestamp
            ON MATCH SET c.source = $source, c.confidence = $confidence, c.timestamp = $timestamp
            WITH c
            MATCH (b:Book {name: $book_name})
            MATCH (ch:Chapter {book: $book_name, number: $chapter_number})
            MERGE (b)-[:CONTAINS]->(c)
            MERGE (ch)-[:CONTAINS]->(c)
            """, content=claim['content'], source=claim['source'], confidence=claim['confidence'], 
                timestamp=claim.get('timestamp', ''), book_name=book_name, chapter_number=chapter_number)
            
            if 'about_entity' in claim:
                session.run("""
                MATCH (c:Claim {content: $content})
                MATCH (e:Entity {name: $entity_name})
                MERGE (c)-[r:ABOUT]->(e)
                SET r.context = $context
                """, content=claim['content'], entity_name=claim['about_entity'], context=claim.get('entity_context', ''))
            
            if 'supports_concept' in claim:
                session.run("""
                MATCH (c:Claim {content: $content})
                MATCH (concept:Concept {name: $concept_name})
                MERGE (c)-[r:SUPPORTS]->(concept)
                SET r.strength = $strength, r.explanation = $explanation
                """, content=claim['content'], concept_name=claim['supports_concept'], 
                    strength=claim.get('support_strength', 0.5), 
                    explanation=claim.get('support_explanation', ''))
            
            for contradicting_claim in claim.get('contradicts', []):
                session.run("""
                MATCH (c1:Claim {content: $content1})
                MERGE (c2:Claim {content: $content2})
                MERGE (c1)-[r:CONTRADICTS]->(c2)
                SET r.explanation = $explanation
                """, content1=claim['content'], content2=contradicting_claim, 
                    explanation=claim.get('contradiction_explanation', ''))

    def _import_concept_relationships(self, session, concept_relationships, book_name, chapter_number):
        for rel in concept_relationships:
            rel_type = self._sanitize_relationship_type(rel['type'])
            session.run(f"""
            MATCH (c1:Concept {{name: $from_}})
            MATCH (c2:Concept {{name: $to}})
            MERGE (c1)-[r:`{rel_type}`]->(c2)
            SET r.strength = $strength, 
                r.context = $context, 
                r.bidirectional = $bidirectional
            WITH c1, c2
            MATCH (b:Book {{name: $book_name}})
            MATCH (ch:Chapter {{book: $book_name, number: $chapter_number}})
            MERGE (b)-[:CONTAINS]->(c1)
            MERGE (b)-[:CONTAINS]->(c2)
            MERGE (ch)-[:CONTAINS]->(c1)
            MERGE (ch)-[:CONTAINS]->(c2)
            """, from_=rel['from'], to=rel['to'], strength=rel['strength'], 
                context=rel['context'], bidirectional=rel['bidirectional'],
                book_name=book_name, chapter_number=chapter_number)

    def _import_poetry(self, session, poetry, book_name, chapter_number):
        for poem in poetry:
            session.run("""
            MERGE (p:Poetry {content: $content})
            SET p.language = $language,
                p.translation = $translation,
                p.source = $source,
                p.poet = $poet
            WITH p
            MATCH (b:Book {name: $book_name})
            MATCH (ch:Chapter {book: $book_name, number: $chapter_number})
            MERGE (b)-[:CONTAINS]->(p)
            MERGE (ch)-[:CONTAINS]->(p)
            """, content=poem['content'], language=poem['language'],
                translation=poem['translation'], source=poem['source'],
                poet=poem['poet'], book_name=book_name, chapter_number=chapter_number)
            
            for concept in poem.get('related_concepts', []):
                session.run("""
                MATCH (p:Poetry {content: $content})
                MATCH (c:Concept {name: $concept_name})
                MERGE (p)-[:RELATES_TO]->(c)
                """, content=poem['content'], concept_name=concept)

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