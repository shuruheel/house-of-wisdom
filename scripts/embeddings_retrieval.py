from logging.handlers import RotatingFileHandler
import math
import os
import json
import numpy as np
from openai import OpenAI, RateLimitError, APIError
import pickle
from scipy.spatial.distance import cosine
import tiktoken
import time
import logging
from neo4j import GraphDatabase
import spacy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingsRetrieval:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.embeddings_file = os.path.join(data_dir, 'embeddings.pkl')
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.book_embeddings = {}
        self.chapter_embeddings = {}
        self.book_contents = {}
        self.chapter_contents = {}
        self.model = "text-embedding-ada-002"
        self.encoding = tiktoken.encoding_for_model(self.model)
        self.max_tokens = 8000

        # Neo4j connection
        neo4j_uri = os.getenv("NEO4J_URI")
        neo4j_user = os.getenv("NEO4J_USER")
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        # Load spaCy model
        self.nlp = spacy.load("en_core_web_sm")

        # Add these new attributes
        self.summaries_dir = os.path.join(data_dir, "summaries")
        self.summary_file_suffix = "_summary.json"
        self.metadata_dir = os.path.join(data_dir, "metadata")
        self.chapter_file_prefix = "chapter_"
        self.chapter_file_suffix = ".json"
        self.current_context_log = os.path.join(data_dir, "current_context.log")

        # Set up a separate logger for relevance calculations
        self.relevance_logger = self.setup_relevance_logger()

    def chunk_text(self, text):
        tokens = self.encoding.encode(text)
        chunks = []
        for i in range(0, len(tokens), self.max_tokens):
            chunk = self.encoding.decode(tokens[i:i + self.max_tokens])
            chunks.append(chunk)
        return chunks

    def generate_embedding(self, text, max_retries=5):
        chunks = self.chunk_text(text)
        embeddings = []

        for chunk in chunks:
            for attempt in range(max_retries):
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=chunk
                    )
                    embeddings.append(response.data[0].embedding)
                    break
                except (RateLimitError, APIError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to generate embedding after {max_retries} attempts: {str(e)}")
                        raise
                    else:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"API error, retrying in {wait_time} seconds...")
                        time.sleep(wait_time)

        # If we have multiple embeddings, average them
        if len(embeddings) > 1:
            return np.mean(embeddings, axis=0).tolist()
        return embeddings[0]

    def load_and_embed_books_and_chapters(self):
        if os.path.exists(self.embeddings_file):
            logger.info(f"Loading embeddings from {self.embeddings_file}")
            with open(self.embeddings_file, 'rb') as f:
                loaded_data = pickle.load(f)
                
            if isinstance(loaded_data, tuple) and len(loaded_data) == 2:
                # Old format: only chapter embeddings and contents
                logger.info("Detected old embedding format. Upgrading to new format...")
                self.chapter_embeddings, self.chapter_contents = loaded_data
                self.book_embeddings = {}
                self.book_contents = {}
                
                # Generate book embeddings and contents from existing chapter data
                for chapter_id, chapter_content in self.chapter_contents.items():
                    book_name = chapter_id.split(":")[0].strip()
                    if book_name not in self.book_contents:
                        self.book_contents[book_name] = ""
                    self.book_contents[book_name] += json.dumps(chapter_content) + "\n\n"
                
                for book_name, book_content in self.book_contents.items():
                    self.book_embeddings[book_name] = self.generate_embedding(book_content)
                
                # Save the updated format
                with open(self.embeddings_file, 'wb') as f:
                    pickle.dump((self.book_embeddings, self.chapter_embeddings, self.book_contents, self.chapter_contents), f)
                
            elif isinstance(loaded_data, tuple) and len(loaded_data) == 4:
                # New format: book and chapter embeddings and contents
                self.book_embeddings, self.chapter_embeddings, self.book_contents, self.chapter_contents = loaded_data
            else:
                raise ValueError("Unknown embedding file format")
        else:
            logger.info("Generating new embeddings")
            
            # Process book summaries
            for summary_file in os.listdir(self.summaries_dir):
                if summary_file.endswith(self.summary_file_suffix):
                    book_name = summary_file[:-len(self.summary_file_suffix)]
                    summary_path = os.path.join(self.summaries_dir, summary_file)
                    with open(summary_path, 'r') as f:
                        summary_data = json.load(f)
                    book_content = json.dumps(summary_data)
                    self.book_contents[book_name] = book_content
                    self.book_embeddings[book_name] = self.generate_embedding(book_content)

            # Process chapter metadata
            for book_dir in os.listdir(self.metadata_dir):
                book_metadata_path = os.path.join(self.metadata_dir, book_dir)
                if os.path.isdir(book_metadata_path):
                    for chapter_file in os.listdir(book_metadata_path):
                        if chapter_file.startswith(self.chapter_file_prefix) and chapter_file.endswith(self.chapter_file_suffix):
                            chapter_path = os.path.join(book_metadata_path, chapter_file)
                            with open(chapter_path, 'r') as f:
                                chapter_data = json.load(f)
                            chapter_content = json.dumps(chapter_data)
                            chapter_id = f"{book_dir}: {chapter_file}"
                            self.chapter_contents[chapter_id] = chapter_data
                            self.chapter_embeddings[chapter_id] = self.generate_embedding(chapter_content)

            logger.info(f"Saving embeddings to {self.embeddings_file}")
            with open(self.embeddings_file, 'wb') as f:
                pickle.dump((self.book_embeddings, self.chapter_embeddings, self.book_contents, self.chapter_contents), f)

        logger.info(f"Loaded embeddings for {len(self.book_embeddings)} books and {len(self.chapter_embeddings)} chapters")

    def extract_key_entities_concepts(self, query):
        doc = self.nlp(query)
        entities = [ent.text.lower() for ent in doc.ents]
        noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]  # Limit to phrases of 3 words or less
        return list(set(entities + noun_chunks))

    def get_related_chapters_from_neo4j(self, keywords):
        with self.neo4j_driver.session() as session:
            result = session.run("""
                UNWIND $keywords AS keyword
                MATCH (c:Chapter)
                WHERE 
                  EXISTS((c)-[:CONTAINS_EVENT]->(:Event)-[:INVOLVES]->(:Entity)) OR
                  EXISTS((c)-[:CONTAINS_EVENT]->(:Event)-[:RELATES_TO]->(:Concept)) OR
                  EXISTS((c)-[:DISCUSSES]->(:Concept)) OR
                  EXISTS((c)-[:CONTAINS_STORY]->(:Story))
                WITH c, keyword
                WHERE 
                  ANY(e IN [(c)-[:CONTAINS_EVENT]->(:Event)-[:INVOLVES]->(entity:Entity) | entity.name] WHERE toLower(e) = toLower(keyword)) OR
                  ANY(co IN [(c)-[:CONTAINS_EVENT]->(:Event)-[:RELATES_TO]->(concept:Concept) | concept.name] WHERE toLower(co) = toLower(keyword)) OR
                  ANY(co IN [(c)-[:DISCUSSES]->(concept:Concept) | concept.name] WHERE toLower(co) = toLower(keyword)) OR
                  ANY(s IN [(c)-[:CONTAINS_STORY]->(story:Story) | story.name] WHERE toLower(s) = toLower(keyword))
                WITH c, count(DISTINCT keyword) AS keyword_matches
                RETURN DISTINCT c.id AS chapter_id, 
                       keyword_matches, 
                       keyword_matches * 1.0 / size($keywords) AS relevance_score
                ORDER BY relevance_score DESC
                LIMIT 10
            """, keywords=keywords)
            return result.data()

    def retrieve_relevant_content(self, query, initial_top_k=20, final_top_k=5):
        self.relevance_logger.info(f"Processing query: {query}")
        
        # Step 1: Use embedding-based method to find initially relevant chapters
        query_embedding = self.generate_embedding(query)
        chapter_similarities = []
        for chapter_id, chapter_embedding in self.chapter_embeddings.items():
            similarity = 1 - cosine(query_embedding, chapter_embedding)
            chapter_similarities.append((chapter_id, similarity))
        
        chapter_similarities.sort(key=lambda x: x[1], reverse=True)
        initial_relevant_chapters = chapter_similarities[:initial_top_k]
        
        self.relevance_logger.info(f"Top {initial_top_k} chapters based on embedding similarity:")
        for chapter_id, similarity in initial_relevant_chapters:
            self.relevance_logger.info(f"  {chapter_id}: {similarity:.4f}")

        # Step 2: Extract key entities and concepts from the query
        key_entities_concepts = self.extract_key_entities_concepts(query)
        self.relevance_logger.info(f"Extracted entities and concepts: {key_entities_concepts}")

        # Step 3: Use Neo4j to find related chapters
        try:
            related_chapters = self.get_related_chapters_from_neo4j(key_entities_concepts)
            self.relevance_logger.info(f"Found {len(related_chapters)} related chapters in Neo4j:")
            for chapter in related_chapters:
                self.relevance_logger.info(f"  {chapter['chapter_id']}: {chapter['relevance_score']:.4f} (matches: {chapter['keyword_matches']})")
        except Exception as e:
            self.relevance_logger.error(f"Error querying Neo4j: {str(e)}")
            related_chapters = []

        # Step 4: Combine embedding similarity with graph-based relevance
        final_scores = {}
        for chapter_id, similarity in initial_relevant_chapters:
            final_scores[chapter_id] = similarity

        for chapter in related_chapters:
            chapter_id = chapter['chapter_id']
            graph_score = chapter['relevance_score']
            if chapter_id in final_scores:
                final_scores[chapter_id] = 0.7 * final_scores[chapter_id] + 0.3 * graph_score
            else:
                final_scores[chapter_id] = graph_score

        final_relevant_chapters = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:final_top_k]

        self.relevance_logger.info("Final relevance scores:")
        for chapter_id, score in final_relevant_chapters:
            self.relevance_logger.info(f"  {chapter_id}: {score:.4f}")

        return [(chapter_id, self.chapter_contents[chapter_id], score) for chapter_id, score in final_relevant_chapters]

    # Remove or comment out the get_dynamic_context and save_current_context methods if they're not being used

    # def get_dynamic_context(self, query, conversation_history, top_k_books=5, chapters_per_book=1, max_top_k=10, decay_factor=0.8):
    #     # ... method implementation ...

    # def save_current_context(self, query, conversation_history, relevant_chapters):
    #     # ... method implementation ...

    def setup_relevance_logger(self):
        logger = logging.getLogger('relevance_logger')
        logger.setLevel(logging.DEBUG)
        
        # Important: This prevents the logger from propagating to the root logger
        logger.propagate = False
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(self.data_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up a rotating file handler
        log_file = os.path.join(log_dir, 'relevance_calculations.log')
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setLevel(logging.DEBUG)
        
        # Create a formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(file_handler)
        
        return logger