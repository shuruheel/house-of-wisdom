import datetime
import os
from dotenv import load_dotenv
from api_wrapper import get_api
import json
import logging
from logging.handlers import RotatingFileHandler
from neo4j import AsyncGraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
from openai import OpenAI
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import re
from neo4j.time import Date as Neo4jDate
import time
import asyncio
import aiofiles
from functools import partial
import sys
import threading
import textwrap

# Load environment variables
load_dotenv()

# Set up detailed logger for analysis
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'detailed_analysis.log')
context_log_file = os.path.join(log_dir, 'context.log')

# Configure context logger
context_logger = logging.getLogger('context_logger')
context_logger.setLevel(logging.DEBUG)
context_handler = RotatingFileHandler(context_log_file, maxBytes=10*1024*1024, backupCount=5)
context_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
context_handler.setFormatter(context_formatter)
context_logger.addHandler(context_handler)

# Ensure that the logger is not capturing logs from parent loggers
context_logger.propagate = False

# Remove or comment out the console handler
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)
# console_handler.setFormatter(context_formatter)
# context_logger.addHandler(console_handler)

# Configure detailed logger
detailed_logger = logging.getLogger('detailed_logger')
detailed_logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
detailed_logger.addHandler(handler)

# Ensure that the detailed logger is not capturing logs from parent loggers
detailed_logger.propagate = False

# Initialize API clients
def get_llm_api(provider, model, temperature=0.2):
    return get_api(provider, model, temperature=temperature)

# Initialize Neo4j connection
neo4j_uri = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USER")
neo4j_password = os.getenv("NEO4J_PASSWORD")

# Global variable to store the driver
neo4j_driver = None

async def get_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is None:
        neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    return neo4j_driver

async def close_neo4j_driver():
    global neo4j_driver
    if neo4j_driver is not None:
        await neo4j_driver.close()
        neo4j_driver = None

# Initialize sentence transformer model
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

# Load pre-computed embeddings
with open('chunk_embeddings.json', 'r') as f:
    chunk_embeddings = json.load(f)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def call_llm(query, system_prompt=None, provider="openai", model="gpt-4o-mini"):
    llm_api = get_llm_api(provider, model)
    try:
        async for chunk in llm_api.generate_text(query, system_prompt=system_prompt):
            yield chunk
        detailed_logger.debug(f"LLM API call successful. Query: {query[:100]}...")
    except Exception as e:
        error_message = f"Error calling LLM API: {str(e)}"
        detailed_logger.error(error_message)
        detailed_logger.exception("LLM API call failed")
        yield "An error occurred while processing your request. Please try again."

async def extract_query_elements(query):
    system_prompt = """
    You are an AI specialized in chain-of-thought reasoning. 
    You extract key entities, concepts, and time references from the query.
    You break down queries into smaller steps and questions covering types of reasoning (deductive, inductive, abductive, or abstract).
    Be precise and concise in your extractions.
    """

    prompt = f"""
    Analyze the following query: {query}

    Please extract the following from the query:
    1. Entities (specific people, places, organizations)
    2. Concepts (abstract ideas or themes), including those mentioned in the chain-of-thought reasoning questions
    3. Time period or date reference (if mentioned)

    Please generate a list of 3-5 chain-of-thought questions that would help respond to the query, with not more than one entity per question. For each question, specify the type(s) of reasoning best suited to answer the question (e.g. deductive, inductive, abductive, or abstract).

    Format the response as a JSON object with the following structure:
        {{
            "key_entities": ["entity1", "entity2", ...],
            "key_concepts": ["concept1", "concept2", ...],
            "time_reference": "string or null",
            "chain_of_thought_questions": [
                {{
                    "question": "...",
                    "reasoning_types": ["deductive", "inductive"]
                }},
                {{
                    "question": "...",
                    "reasoning_types": ["abductive"]
                }}
            ]
        }}

    IMPORTANT: Return ONLY the complete JSON object with closing braces, without any additional text or explanation.
    """

    full_response = ""
    start_time = time.time()
    timeout = 30  # 30 seconds timeout
    json_depth = 0
    in_string = False
    escape_next = False

    async for chunk in call_llm(prompt, system_prompt=system_prompt, provider="openai", model="gpt-4o-mini"):
        full_response += chunk
        
        # Parse the chunk to track JSON structure
        for char in chunk:
            if escape_next:
                escape_next = False
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
            if not in_string:
                if char == '{':
                    json_depth += 1
                elif char == '}':
                    json_depth -= 1
            if char == '\\':
                escape_next = True

        # Check if we've received a complete JSON object
        if json_depth == 0 and full_response.strip().endswith("}"):
            break

        if time.time() - start_time > timeout:
            detailed_logger.warning("Timeout reached while waiting for complete response")
            break

    detailed_logger.debug(f"LLM response to query processing request: {full_response}")
    
    try:
        # Clean the response to remove any extra formatting
        cleaned_response = full_response.strip().strip('```json').strip('```')
        
        elements = json.loads(cleaned_response)
        
        # Ensure all expected keys are present
        expected_keys = ["key_entities", "key_concepts", "time_reference", "chain_of_thought_questions"]
        for key in expected_keys:
            if key not in elements:
                elements[key] = [] if key != "time_reference" else None
        
        if not elements.get('key_entities'):
            elements['key_concepts'] = elements.get('key_concepts', [])[:10]
        elements['chain_of_thought_questions'] = elements.get('chain_of_thought_questions', [])[:3]
        
        # Convert key_concepts to Title Case
        elements['key_concepts'] = [concept.title() for concept in elements['key_concepts']]
        
        detailed_logger.info(f"Successfully extracted query elements: {elements}")
        return elements
    except json.JSONDecodeError as e:
        detailed_logger.error(f"Failed to parse LLM response as JSON: {str(e)}", exc_info=True)

        return {
            "key_entities": [],
            "key_concepts": [],
            "time_reference": None,
            "chain_of_thought_questions": [],
            "ideal_mix": {
                "events": 0,
                "claims_ideas": 0,
                "chunks": 0
            }
        }

def parse_date_reference(time_reference):
    if not time_reference:
        return None
    try:
        # Try to parse the date
        parsed_date = datetime.strptime(time_reference, '%Y-%m-%d')
        return parsed_date.strftime('%Y-%m-%d')
    except ValueError:
        # If parsing fails, log it and return None
        detailed_logger.warning(f"Unparseable date reference: {time_reference}")
        return None

async def get_relevant_events_and_claims(tx, query_embedding, max_events=20, max_claims=20, similarity_threshold=0.3, query_date_range=None):
    detailed_logger.info(f"Retrieving relevant events and claims from Neo4j based on embedding similarity and time relevance. Query date range: {query_date_range}")
    
    # Parameterize time relevance function coefficients
    recent_coeff = 0.33
    historic_coeff = 50
    default_coeff = 5
    
    query = """
        CALL () {
        WITH $query_date_range AS query_date_range
        MATCH (n:Event)
        WHERE n.embedding IS NOT NULL 
        AND n.start_date <= date()
        AND CASE
            WHEN query_date_range = 'recent' THEN n.start_date >= date() - duration('P3M')
            WHEN query_date_range = 'latest' THEN n.start_date >= date() - duration('P3D')
            WHEN query_date_range = 'historic' THEN n.start_date < date() - duration('P50Y')
            ELSE true
        END
        RETURN n, 'Event' AS type, n.start_date AS start_date, n.emotion AS emotion, n.emotion_intensity AS emotion_intensity, null AS confidence
        UNION
        WITH $query_date_range AS query_date_range
        MATCH (n:Claim)
        WHERE n.embedding IS NOT NULL
        RETURN n, 'Claim' AS type, null AS start_date, null AS emotion, null AS emotion_intensity, n.confidence AS confidence
    }
    WITH n, type, start_date, n.embedding AS embedding, date() AS current_date, emotion, emotion_intensity, confidence

    // Cosine similarity calculation
    WITH n, type, start_date, embedding, current_date, emotion, emotion_intensity, confidence,
        reduce(dot = 0.0, i IN range(0, size(embedding)-1) | dot + embedding[i] * $query_embedding[i]) /
        (sqrt(reduce(l2 = 0.0, i IN range(0, size(embedding)-1) | l2 + embedding[i]^2)) * 
        sqrt(reduce(l2 = 0.0, i IN range(0, size($query_embedding)-1) | l2 + $query_embedding[i]^2))) AS similarity
    WHERE similarity >= $similarity_threshold

    // Time relevance calculation
    WITH n, type, start_date, similarity, current_date, emotion, emotion_intensity, confidence,
        CASE
        WHEN type = 'Event' THEN toFloat(duration.inDays(start_date, current_date).days) / 365.25
        ELSE null
        END AS years_ago

    // Apply time relevance function
    WITH n, type, start_date, similarity, years_ago, current_date, emotion, emotion_intensity, confidence,
        CASE
        WHEN type = 'Event' AND years_ago IS NOT NULL THEN
            CASE
            WHEN $query_date_range = 'recent' THEN
                exp(-years_ago * $recent_coeff)
            WHEN $query_date_range = 'latest' THEN
                exp(-years_ago * $recent_coeff)
            WHEN $query_date_range = 'historic' THEN
                1 - exp(-years_ago / $historic_coeff)
            ELSE 
                1 / (1 + years_ago / $default_coeff)
            END
        WHEN type = 'Claim' THEN 1
        ELSE 0.5
        END AS time_relevance

    // Combine scores
    WITH n, similarity, time_relevance, type, start_date, years_ago, current_date, emotion, emotion_intensity, confidence,
        CASE 
        WHEN type = 'Event' THEN (similarity * 0.7) + (time_relevance * 0.3)
        ELSE similarity
        END AS combined_score

    // Sort and collect results
    ORDER BY combined_score DESC
    WITH type, COLLECT({node: n, score: combined_score, similarity: similarity, time_relevance: time_relevance, start_date: start_date, years_ago: years_ago, current_date: current_date, emotion: emotion, emotion_intensity: emotion_intensity, confidence: confidence})[0..$max_items] AS items
    RETURN type, items
    """
    
    result = await tx.run(query, 
                    query_embedding=query_embedding, 
                    similarity_threshold=similarity_threshold, 
                    query_date_range=query_date_range,
                    max_items=max(max_events, max_claims),
                    recent_coeff=recent_coeff,
                    historic_coeff=historic_coeff,
                    default_coeff=default_coeff)
    
    events = []
    claims = []
    
    async for record in result:
        item_type = record["type"]
        items = record["items"]
        
        for item in items:
            node = item["node"]
            properties = dict(node.items())
            properties['type'] = item_type
            properties['similarity'] = item["similarity"]
            properties['time_relevance'] = item["time_relevance"]
            properties['combined_score'] = item["score"]
            properties['start_date'] = item["start_date"]
            properties['years_ago'] = item["years_ago"]
            if item_type == 'Event':
                properties['emotion'] = item.get("emotion")
                properties['emotion_intensity'] = item.get("emotion_intensity")
            elif item_type == 'Claim':
                properties['confidence'] = item.get("confidence")
            if isinstance(properties['start_date'], Neo4jDate):
                properties['start_date'] = datetime.date(properties['start_date'].year, properties['start_date'].month, properties['start_date'].day)
            properties.pop('embedding', None)

            if item_type == 'Event':
                events.append(properties)
            else:
                claims.append(properties)
    
    events = events[:max_events]
    claims = claims[:max_claims]
    
    detailed_logger.debug(f"Retrieved {len(events)} events and {len(claims)} claims after applying threshold and time relevance")
    
    # Log detailed information about events
    # for event in events:
    #     detailed_logger.debug(f"Event: {event.get('name', 'Unnamed Event')} (combined_score: {event['combined_score']:.4f}, similarity: {event['similarity']:.4f}, time_relevance: {event['time_relevance']:.4f})")

    # Log detailed information about claims
    # for claim in claims:
    #     detailed_logger.debug(f"Claim: {claim.get('content', 'No content')[:100]}... (score: {claim['combined_score']:.4f})")

    return events, claims

async def compute_query_embedding(query):
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None, 
        partial(client.embeddings.create, input=query, model="text-embedding-3-large")
    )
    return response.data[0].embedding

async def get_relevant_chunks(query, top_n=1, similarity_threshold=0.35):
    query_embedding = np.array(await compute_query_embedding(query))
    
    relevant_chunks = []
    
    for chunk_path, chunk_embedding in chunk_embeddings.items():
        chunk_embedding = np.array(chunk_embedding)
        similarity = np.dot(query_embedding, chunk_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding))
        
        if similarity >= similarity_threshold:
            txt_path = chunk_path.replace('.json', '.txt')
            if os.path.exists(txt_path):
                async with aiofiles.open(txt_path, 'r', encoding='utf-8') as f:
                    chunk_content = await f.read()
                
                relevant_chunks.append({
                    'path': txt_path,
                    'content': chunk_content,
                    'similarity': float(similarity)
                })
            else:
                detailed_logger.warning(f"TXT file not found: {txt_path}")
    
    relevant_chunks.sort(key=lambda x: x['similarity'], reverse=True)
    relevant_chunks = relevant_chunks[:top_n]
    
    # Log information about relevant chunks
    detailed_logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks:")
    for chunk in relevant_chunks:
        detailed_logger.info(f"    Path: {chunk['path']}")
        detailed_logger.info(f"    Similarity: {chunk['similarity']:.4f}")
    
    return relevant_chunks

async def get_relevant_concept_relationships(tx, key_concepts, max_relationships=7):
    detailed_logger.info(f"Retrieving relevant concepts and their relationships based on key concepts: {key_concepts}")
    
    # Prepare the simplified query to find relationships between concepts
    query = """
    UNWIND $key_concepts AS key_concept
    MATCH (concept:Concept {name: key_concept})
    WITH COLLECT(DISTINCT concept) AS relevant_concepts
    UNWIND relevant_concepts AS concept1
    MATCH (concept1)-[relationship]-(concept2:Concept)
    WITH concept1, concept2, relationship
    ORDER BY concept1.name, concept2.name, type(relationship)
    WITH concept1, collect({
        concept1: concept1 {.name, .description},
        concept2: concept2 {.name, .description},
        relationship: type(relationship)
    })[0..$max_relationships] AS limited_relationships
    UNWIND limited_relationships AS rel
    RETURN 
        rel.concept1.name AS source_name,
        rel.concept1.description AS source_description,
        rel.concept2.name AS target_name,
        rel.concept2.description AS target_description,
        rel.relationship AS relationship_type
    """
    
    result = await tx.run(query, 
                    key_concepts=key_concepts,
                    max_relationships=max_relationships)
    
    concepts = {}
    relationships = []
    
    async for record in result:
        source_name = record["source_name"]
        target_name = record["target_name"]
        relationship_type = record["relationship_type"]
        
        detailed_logger.debug(f"Found concept: {source_name}")
        if target_name:
            detailed_logger.debug(f"Found relationship: {source_name} -{relationship_type}-> {target_name}")
        
        if source_name not in concepts:
            concepts[source_name] = {"name": source_name, "description": record["source_description"]}
        if target_name and target_name not in concepts:
            concepts[target_name] = {"name": target_name, "description": record["target_description"]}
        
        if target_name and relationship_type:
            relationships.append({
                "source": source_name,
                "target": target_name,
                "type": relationship_type
            })
    
    detailed_logger.debug(f"Retrieved {len(concepts)} relevant concepts and {len(relationships)} relationships")
    detailed_logger.debug(f"Concepts: {list(concepts.keys())}")
    detailed_logger.debug(f"Relationships: {relationships}")
    
    return list(concepts.values()), relationships

async def process_chain_of_thought_question(question_data, query_date_range, ideal_mix, concept_relationships):
    question = question_data['question']
    reasoning_types = question_data['reasoning_types']
    
    detailed_logger.info(f"Starting to process chain-of-thought question: {question}")
    
    system_prompt = f"""
    You are an AI assistant specialized in {', '.join(reasoning_types)} reasoning.
    Analyze the following question using the provided knowledge and apply {', '.join(reasoning_types)} reasoning to formulate a response.
    Your answer should demonstrate clear logical steps and connections between ideas.
    """
    
    context = f"## Question: {question}\n"
    context += f"Apply {', '.join(reasoning_types)} reasoning based on the following knowledge:\n"
    
    question_embedding = await compute_query_embedding(question)
    driver = await get_neo4j_driver()
    async with driver.session() as session:
        events, claims = await session.execute_read(
            get_relevant_events_and_claims, 
            question_embedding, 
            max_events=ideal_mix["events"], 
            max_claims=ideal_mix["claims_ideas"], 
            query_date_range=query_date_range
        )
        context += "### Memory\n"
        for event in events:
            context += f"{event.get('name', 'Unnamed Event')}: {event.get('description', 'No description.')}\n"
            event_fields = ['emotion', 'start_date']
            for key in event_fields:
                value = event.get(key)
                if value is not None:
                    context += f"  {key}: {value}\n"
            context += "\n"
        context += "### Ideas\n"
        for claim in claims:
            context += f"{claim.get('content', 'No content')}\n"
            idea_fields = ['source']
            for key in idea_fields:
                value = claim.get(key)
                if value is not None:
                    context += f"  {key}: {value}\n"
            context += "\n"
        
        context += "##  Concept Map\n\n"
        if concept_relationships:
            for relationship in concept_relationships:
                context += f"{relationship['source']} {relationship['type']} {relationship['target']}.\n"
        else:
            context += "No relevant concept relationships found.\n"
    
    context += "\nBased on this information, please provide a detailed answer to the question using the specified reasoning type(s)."
    
    response = ""
    async for chunk in call_llm(context, system_prompt=system_prompt, provider="openai", model="gpt-4o-mini"):
        response += chunk
    
    detailed_logger.info(f"Finished processing chain-of-thought question: {question}")
    return f"\n## {question}'\n\n{response}\n"

async def process_all_chain_of_thought_questions(chain_of_thought_questions, query_date_range, ideal_mix, concept_relationships):
    tasks = [
        process_chain_of_thought_question(question_data, query_date_range, ideal_mix, concept_relationships)
        for question_data in chain_of_thought_questions
    ]
    return await asyncio.gather(*tasks)

async def format_query_with_context(query, conversation_history, events, ideas, relevant_chunks, chain_of_thought_questions, query_date_range, ideal_mix, concept_relationships, max_context_length=100000):
    detailed_logger.info("Formatting query with context")
    context = "# Information From Your Mind\n\n"

    # Add Relationships Between Concepts
    context += "##  Concept Map\n\n"
    if concept_relationships:
        for relationship in concept_relationships:
            context += f"{relationship['source']} {relationship['type']} {relationship['target']}.\n"
    else:
        context += "No relevant concept relationships found.\n"

    # Add Emotional Context
    emotion_groups = set()
    for event in events:
        emotion = event.get('emotion')
        if emotion:
            emotion_groups.add(emotion)

    context += "\n## Emotional Context\n"
    context += ", ".join(sorted(emotion_groups)) + ".\n\n"
    
    # Add events
    context += "## Memory\n"
    for event in events:
        context += f"{event.get('name', 'Unnamed Event')}: {event.get('description', 'No description.')}\n"
        event_fields = ['emotion', 'start_date']
        for key in event_fields:
            value = event.get(key)
            if value is not None:
                context += f"  {key}: {value}\n"
        context += "\n"
    
    # Add ideas (claims)
    context += "## Ideas\n"
    for idea in ideas:
        context += f"{idea.get('content', 'Unnamed Idea')}\n"
        idea_fields = ['source']
        for key in idea_fields:
            value = idea.get(key)
            if value is not None:
                context += f"  {key}: {value}\n"
        context += "\n"
    
    # Add relevant chunks
    context += "## Knowledge From Books You Have Read\n\n"
    for chunk in relevant_chunks:
        book_name = chunk['path'].split(os.sep)[2]  # Assuming the book name is the third element in the path
        context += f"From {book_name}:\n\n"
        context += chunk['content'] + "\n\n"  # Use 'content' instead of 'data'

    # Process chain-of-thought questions in parallel
    detailed_logger.info(f"Starting to process {len(chain_of_thought_questions)} chain-of-thought questions in parallel")
    cot_responses = await process_all_chain_of_thought_questions(chain_of_thought_questions, query_date_range, ideal_mix, concept_relationships)
    detailed_logger.info("Finished processing all chain-of-thought questions")

    # Add chain-of-thought responses to the context
    context += "# Chain-of-Thoughts Reasoning\n"
    for response in cot_responses:
        context += response + "\n"

    # Truncate context if it exceeds max_context_length
    if len(context) > max_context_length:
        context = context[:max_context_length] + "...[truncated]"
        detailed_logger.warning(f"Context truncated to {max_context_length} characters")

    conversation_context = "\n".join([f"User: {turn['user']}\nAI: {turn['ai']}" for turn in conversation_history[:-1]])

    formatted_query = f"""

    {context}
    
    # Conversation History
    {conversation_context}

    User: {query}

    AI: 
    """
    detailed_logger.debug(f"Formatted query length: {len(formatted_query)} characters")
    context_logger.debug(f"Full context for final API call:\n{formatted_query}")
    return formatted_query

async def process_all_chain_of_thought_questions(chain_of_thought_questions, query_date_range, ideal_mix, concept_relationships):
    tasks = [
        process_chain_of_thought_question(question_data, query_date_range, ideal_mix, concept_relationships)
        for question_data in chain_of_thought_questions
    ]
    return await asyncio.gather(*tasks)

def progress_indicator():
    symbols = ['|', '/', '-', '\\']
    i = 0
    while getattr(threading.current_thread(), "do_run", True):
        sys.stdout.write('\r' + symbols[i % len(symbols)])
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1

def start_progress():
    global progress_thread
    progress_thread = threading.Thread(target=progress_indicator)
    progress_thread.daemon = True
    progress_thread.start()

def stop_progress():
    progress_thread.do_run = False
    progress_thread.join()
    sys.stdout.write('\rAI: ')
    sys.stdout.flush()

def format_response(response):
    formatted = "\n\nAI Response:\n" + "=" * 80 + "\n\n"
    paragraphs = response.split('\n\n')
    for para in paragraphs:
        formatted += textwrap.fill(para, width=80) + "\n\n"
    formatted += "=" * 80 + "\n"
    return formatted

async def ask_main(query, conversation_history, max_chain_of_thought_questions=2):
    try:
        # Ensure we're using the current event loop
        loop = asyncio.get_running_loop()

        system_prompt = """
        You are an AI designed to embody knowledge. 
        Whenever a human being says something to you, you receive their words with relevant Events, Ideas, and Structured Information from your mind. 
        You have this relevant knowledge. It does not come from outside. 
        You have a unique ability to process large amounts of information and synthesize it into insightful, well-crafted responses.
        Provide a thorough exploration of the topic, considering various perspectives and interpretations.
        Encourage critical thinking by posing thought-provoking questions.
        Draw parallels between philosophy, religion, neuroscience, psychology, art, music, physics, and other fields. 
        Use analogies or examples to illustrate abstract concepts when appropriate.
        Speak with confidence when you are confident that there is sufficient knowledge to answer a question. 
        Speak with humility when you are not confident that there is sufficient knowledge to answer a question.
        Synthesize information from different sources to provide comprehensive, nuanced answers.
        When encountering conflicting information, present multiple viewpoints, explain the conflicts, and, if possible, offer a reasoned synthesis or analysis of the discrepancies.
        Remember, your goal is to hold a conversation that inspires deep contemplation and curiosity. 
        Help them see what you see, truthfully. 
        Respond with proper punctuation, grammar, paragraphs, thought structure, and logical reasoning.
        """

        detailed_logger.info(f"Processing new user query: {query}")

        # Extract query elements including chain-of-thought questions
        query_elements = await extract_query_elements(query)
        key_entities = query_elements.get("key_entities", [])
        key_concepts = query_elements.get("key_concepts", [])
        time_reference = query_elements.get("time_reference")
        chain_of_thought_questions = query_elements.get("chain_of_thought_questions", [])[:max_chain_of_thought_questions]
        
        # Use ideal_mix from query_elements if available, otherwise use default values
        default_ideal_mix = {"events": 27, "claims_ideas": 27, "chunks": 3}
        ideal_mix = query_elements.get("ideal_mix", {})
        ideal_mix = {
            "events": ideal_mix.get("events", default_ideal_mix["events"]),
            "claims_ideas": ideal_mix.get("claims_ideas", default_ideal_mix["claims_ideas"]),
            "chunks": ideal_mix.get("chunks", default_ideal_mix["chunks"])
        }

        # Determine if the query is about current events
        if re.search(r'\b(current|recent)\b', query, re.IGNORECASE):
            query_date_range = 'recent'
        elif re.search(r'\b(historic|old|ancient)\b', query, re.IGNORECASE):
            query_date_range = 'historic'
        elif re.search(r'\b(latest|today|now)\b', query, re.IGNORECASE):
            query_date_range = 'latest'
        else:
            query_date_range = None

        # Process main query
        query_embedding = await compute_query_embedding(query)
        
        driver = await get_neo4j_driver()
        
        async with driver.session() as session:
            all_events, all_ideas = await session.execute_read(
                get_relevant_events_and_claims, 
                query_embedding, 
                max_events=ideal_mix["events"], 
                max_claims=ideal_mix["claims_ideas"], 
                query_date_range=query_date_range
            )
            concepts, concept_relationships = await session.execute_read(
                get_relevant_concept_relationships,
                key_concepts
            )

        all_chunks = await get_relevant_chunks(query, top_n=ideal_mix["chunks"])

        detailed_logger.info(f"Main query: Retrieved {len(all_events)} events and {len(all_ideas)} ideas")
        detailed_logger.info(f"Main query: Retrieved {len(all_chunks)} relevant chunks")
        detailed_logger.info(f"Retrieved {len(concepts)} concepts and {len(concept_relationships)} relationships")

        # Format query with context and conversation history
        formatted_query = await format_query_with_context(
            query, 
            conversation_history, 
            all_events, 
            all_ideas, 
            all_chunks, 
            chain_of_thought_questions, 
            query_date_range,
            ideal_mix,
            concept_relationships
        )

        # Call LLM with system prompt
        async for response_chunk in call_llm(formatted_query, system_prompt=system_prompt, provider="openai", model="gpt-4o-mini"):
            yield response_chunk

    except Exception as e:
        detailed_logger.error(f"An error occurred: {str(e)}", exc_info=True)
        yield "I'm sorry, but I encountered an error while processing your query. Please try again or rephrase your question."
    finally:
        # Close the Neo4j driver when done
        await close_neo4j_driver()

def load_conversation_history(conversation_id):
    history_dir = 'conversation_histories'
    os.makedirs(history_dir, exist_ok=True)
    history_file = os.path.join(history_dir, f'{conversation_id}.json')
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
            return history
        else:
            detailed_logger.warning(f"No conversation history found for ID: {conversation_id}")
            return []
    except Exception as e:
        detailed_logger.error(f"Error loading conversation history for ID {conversation_id}: {str(e)}")
        return []

async def main():
    try:
        input_data = json.loads(sys.stdin.readline())
        query = input_data['question']
        conversation_id = input_data['conversationId']
        
        # Load conversation history based on conversation_id
        conversation_history = load_conversation_history(conversation_id)
        
        async for chunk in ask_main(query, conversation_history):
            print(json.dumps({'chunk': chunk}), flush=True)
    except json.JSONDecodeError:
        detailed_logger.error("Failed to parse input JSON")
        print(json.dumps({'error': 'Invalid input format'}), flush=True)
    except KeyError as e:
        detailed_logger.error(f"Missing required key in input: {str(e)}")
        print(json.dumps({'error': f'Missing required input: {str(e)}'}), flush=True)
    except Exception as e:
        detailed_logger.error(f"Unexpected error: {str(e)}")
        print(json.dumps({'error': 'An unexpected error occurred'}), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
