import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

class Neo4jPopulator:
    def __init__(self):
        neo4j_uri = os.getenv("NEO4J_URI2")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD2")
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.counters = {
            'chapters': 0,
            'stories': 0,
            'events': 0,
            'entities': 0,
            'concepts': 0,
            'claims': 0,
            'contains_story': 0,
            'contains_event': 0,
            'involves': 0,
            'relates_to': 0,
            'discusses': 0,
            'makes_claim': 0
        }

    def close(self):
        self.driver.close()

    def clear_database(self):
        with self.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n")
            return result.consume().counters.nodes_deleted

    def add_chapter(self, chapter_id, content):
        with self.driver.session() as session:
            session.run("""
                CREATE (c:Chapter {id: $id, content: $content})
            """, id=chapter_id, content=content)
            self.counters['chapters'] += 1

    def add_story(self, name, description):
        with self.driver.session() as session:
            session.run("""
                MERGE (s:Story {name: $name})
                SET s.description = $description
            """, name=name, description=description)
            self.counters['stories'] += 1

    def add_event(self, name, description):
        with self.driver.session() as session:
            session.run("""
                MERGE (e:Event {name: $name})
                SET e.description = $description
            """, name=name, description=description)
            self.counters['events'] += 1

    def add_entity(self, name):
        with self.driver.session() as session:
            session.run("""
                MERGE (e:Entity {name: $name})
            """, name=name)
            self.counters['entities'] += 1

    def add_concept(self, name, description=''):
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Concept {name: $name})
                SET c.description = $description
            """, name=name, description=description)
            self.counters['concepts'] += 1

    def add_claim(self, content, source, confidence):
        with self.driver.session() as session:
            session.run("""
                MERGE (c:Claim {content: $content})
                SET c.source = $source, c.confidence = $confidence
            """, content=content, source=source, confidence=confidence)
            self.counters['claims'] += 1

    def add_relationship(self, from_node, to_node, rel_type):
        with self.driver.session() as session:
            query = (
                "MATCH (n1) "
                "WHERE n1.id = $from_node OR n1.name = $from_node "
                "MATCH (n2) "
                "WHERE n2.id = $to_node OR n2.name = $to_node "
                f"MERGE (n1)-[r:{rel_type}]->(n2)"
            )
            session.run(query, from_node=from_node, to_node=to_node)
            self.counters[rel_type.lower()] += 1

def populate_database(data_dir, metadata_dir):
    populator = Neo4jPopulator()

    # Clear existing data
    nodes_deleted = populator.clear_database()
    print(f"Cleared {nodes_deleted} nodes from the database.")

    # Get total number of chapters for progress bar
    total_chapters = sum(
        len([f for f in files if f.startswith("chapter_") and f.endswith(".json")])
        for _, _, files in os.walk(metadata_dir)
    )

    # Process each book directory in the metadata directory
    with tqdm(total=total_chapters, desc="Populating database", unit="chapter") as pbar:
        for book_dir in os.listdir(metadata_dir):
            book_metadata_path = os.path.join(metadata_dir, book_dir)
            if os.path.isdir(book_metadata_path):
                for chapter_file in os.listdir(book_metadata_path):
                    if chapter_file.startswith("chapter_") and chapter_file.endswith(".json"):
                        chapter_path = os.path.join(book_metadata_path, chapter_file)
                        try:
                            with open(chapter_path, 'r') as f:
                                data = json.load(f)
                            
                            chapter_id = f"{book_dir}: {chapter_file}"
                            content = json.dumps(data)  # Store the entire JSON as content
                            
                            populator.add_chapter(chapter_id, content)
                            
                            # Process stories
                            for story in data.get('stories', []):
                                story_name = story.get('name')
                                if story_name:
                                    populator.add_story(story_name, story.get('description', ''))
                                    populator.add_relationship(chapter_id, story_name, 'CONTAINS_STORY')

                            # Process events
                            for event in data.get('events', []):
                                event_name = event.get('name')
                                if event_name:
                                    populator.add_event(event_name, event.get('description', ''))
                                    populator.add_relationship(chapter_id, event_name, 'CONTAINS_EVENT')
                                    
                                    # Process involved entities
                                    for entity in event.get('involved_entities', []):
                                        if entity:
                                            populator.add_entity(entity)
                                            populator.add_relationship(event_name, entity, 'INVOLVES')

                                    # Process related concepts
                                    for concept in event.get('related_concepts', []):
                                        if concept:
                                            populator.add_concept(concept)
                                            populator.add_relationship(event_name, concept, 'RELATES_TO')

                            # Process concepts
                            for concept in data.get('concepts', []):
                                concept_name = concept.get('name')
                                if concept_name:
                                    populator.add_concept(concept_name, concept.get('description', ''))
                                    populator.add_relationship(chapter_id, concept_name, 'DISCUSSES')

                            # Process claims
                            for claim in data.get('claims', []):
                                claim_content = claim.get('content')
                                if claim_content:
                                    populator.add_claim(claim_content, claim.get('source', ''), claim.get('confidence', 0))
                                    populator.add_relationship(chapter_id, claim_content, 'MAKES_CLAIM')

                            pbar.update(1)
                        except Exception as e:
                            print(f"Error processing {chapter_path}: {str(e)}")

    populator.close()
    return populator.counters

if __name__ == "__main__":
    data_dir = "data"
    metadata_dir = os.path.join(data_dir, "metadata")
    counters = populate_database(data_dir, metadata_dir)
    print("Database population complete.")
    print("Summary:")
    print(f"Chapters created: {counters['chapters']}")
    print(f"Stories created: {counters['stories']}")
    print(f"Events created: {counters['events']}")
    print(f"Entities created: {counters['entities']}")
    print(f"Concepts created: {counters['concepts']}")
    print(f"Claims created: {counters['claims']}")
    print(f"CONTAINS_STORY relationships: {counters['contains_story']}")
    print(f"CONTAINS_EVENT relationships: {counters['contains_event']}")
    print(f"INVOLVES relationships: {counters['involves']}")
    print(f"RELATES_TO relationships: {counters['relates_to']}")
    print(f"DISCUSSES relationships: {counters['discusses']}")
    print(f"MAKES_CLAIM relationships: {counters['makes_claim']}")