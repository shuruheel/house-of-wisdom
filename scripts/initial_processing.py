import os
import json
import logging
import traceback
from pathlib import Path
import asyncio
from data_loader import load_book_content, get_all_book_names
from text_preprocessor import preprocess_text, split_by_markdown_headings
from api_wrapper import get_api
import textwrap

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize API clients
gemini_api = get_api("google", "gemini-1.5-pro-exp-0827", temperature=0.1)
gpt4_api = get_api("openai", "gpt-4o", temperature=0.1)
anthropic_api = get_api("anthropic", "claude-3-5-sonnet-20240620", temperature=0.1)
groq_api = get_api("groq", "llama-3.1-70b-versatile", temperature=0.1)

async def safe_api_call(api, prompt):
    """
    Make an async API call with error handling.
    """
    try:
        response_generator = api.generate_text(prompt)
        full_response = ""
        async for chunk in response_generator:
            full_response += chunk
        
        # Check if the response is already a valid JSON string
        try:
            json_response = json.loads(full_response)
            return json_response
        except json.JSONDecodeError:
            # If it's not valid JSON, try to extract JSON from the response
            json_start = full_response.find('{')
            json_end = full_response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_string = full_response[json_start:json_end]
                return json.loads(json_string)
            else:
                raise ValueError("No valid JSON found in the response")
    except Exception as e:
        logger.error(f"API call failed: {str(e)}\nRaw response: {full_response}")
        return None

async def extract_book_info(content, book_name):
    """
    Use Google Gemini 1.5 Pro to extract book summary information.
    """
    prompt = f"""
    ## Objective
    Analyze the following book content and generate a brief summary highlighting key themes, stories, and conclusions. 

    ## IMPORTANT REQUIREMENTS
    Return a complete JSON object without any additional markdown or comments. 
    Make sure that the JSON object isn't truncated due to token limits. 
    Response should begin with {{ and end with }}.

    ## Response JSON Format
    {{
        "book": {{
            "title": "{book_name}",
            "summary": "brief_summary"
        }}
    }}

    ## Book Content
    {content}
    """
    
    return await safe_api_call(gemini_api, prompt)

async def analyze_chapter(heading, content, book_name):
    """
    Analyze a chapter of the book using the appropriate API based on content length.
    """
    system_prompt = """You are an AI assistant tasked with analyzing book content and extracting structured information."""
    
    prompt = f"""
    Analyze the following section of the book titled "{book_name}" and provide information in a format suitable for a Neo4j graph database.
    Extract the most important Stories, Events, Entities, Concepts, Mathematical Formulas, Emotional States, Cross-Lingual Links, Claims, and Concept Relationships mentioned in the section. 

    IMPORTANT REQUIREMENTS:
    Return a complete JSON object without any additional markdown or comments. 
    Make sure that the JSON object isn't truncated due to token limits. 
    Response should begin with {{ and end with }}.

    Neo4j Graph Database Structure:
    CREATE 
    (:Book {{title: String, summary: String}}),
    (:Story {{name: String, description: String, version: String}}),
    (:Event {{
        name: String,
        description: String,
        start_date: Date,
        end_date: Date,
        date_precision: String  # 'DAY', 'MONTH', 'YEAR', 'DECADE', 'CENTURY'
    }}),
    (:Entity {{name: String, type: String, description: String, language: String}}),
    (:Concept {{name: String, description: String, language: String}}),
    (:MathematicalFormula {{name: String, formula: String, description: String}}),
    (:Poetry {{content: String, language: String, translation: String, source: String}}),
    (:EmotionalState {{primary_emotion: String, secondary_emotions: List<String>, intensity: Float, context: String, timestamp: DateTime}}),
    (:Claim {{content: String, source: String, confidence: Float, timestamp: DateTime}})

    CREATE
    (:Book)-[:CONTRIBUTES_TO]->(:Story),
    (:Story)-[:INCLUDES]->(:Event),
    (:Event)-[:NEXT]->(:Event),
    (:Event)-[:INVOLVES]->(:Entity),
    (:Event)-[:RELATES_TO]->(:Concept),
    (:Entity)-[:RELATES_TO {{type: String, description: String}}]->(:Entity),
    (:Concept)-[:RELATES_TO {{type: String, description: String}}]->(:Concept),
    (:Book)-[:CONTAINS]->(:MathematicalFormula),
    (:MathematicalFormula)-[:DESCRIBES]->(:Concept),
    (:Poetry)-[:WRITTEN_BY]->(:Entity),
    (:Poetry)-[:RELATES_TO]->(:Concept),
    (:Poetry)-[:APPEARS_IN]->(:Book),
    (:Event)-[:EVOKES]->(:EmotionalState),
    (:Entity)-[:EXPERIENCES]->(:EmotionalState),
    (e1:Entity)-[:SAME_AS {{confidence: Float}}]->(e2:Entity),
    (c1:Concept)-[:SAME_AS {{confidence: Float}}]->(c2:Concept),
    (:Claim)-[:ABOUT]->(:Entity),
    (:Claim)-[:SUPPORTS]->(:Concept),
    (:Claim)-[:CONTRADICTS]->(:Claim),
    (:Book)-[:CONTAINS]->(:Claim),
    (c1:Concept)-[r:RELATES_TO {{
        type: String,
        strength: Float,
        context: String,
        bidirectional: Boolean
    }}]->(c2:Concept)

    Response JSON Format:
    {{
        "stories": [
            {{
                "name": "story_name",
                "description": "A description of this timeline of events",
                "version": "version_identifier",
                "events": ["event1", "event2", ...]
            }},
            ...
        ],
        "events": [
            {{
                "name": "event_name",
                "description": "event_description",
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
                "date_precision": "DAY/MONTH/YEAR/DECADE/CENTURY",
                "involved_entities": ["entity1", "entity2", ...],
                "related_concepts": ["concept1", "concept2", ...],
                "emotion": "emotion_name",
                "emotion_intensity": 0.0 to 1.0,
                "next_event": "next_event_name"
            }},
            ...
        ],
        "entities": [
            {{
                "name": "entity_name",
                "type": "person/place/organization",
                "description": "entity_description",
                "language": "en",
                "related_entities": [
                    {{
                        "name": "related_entity_name",
                        "relationship_type": "type_of_relationship",
                        "relationship_description": "description_of_relationship"
                    }},
                    ...
                ]
            }},
            ...
        ],
        "concepts": [
            {{
                "name": "concept_name",
                "description": "concept_description",
                "language": "en"
            }},
            ...
        ],
        "concept_relationships": [
            {{
                "from": "concept1",
                "to": "concept2",
                "type": "relationship_type",
                "strength": 0.8,
                "context": "Description of the context in which this relationship applies",
                "bidirectional": true,
            }},
            ...
        ],
        "mathematical_formulas": [
            {{
                "name": "formula_name",
                "formula": "formula_representation",
                "description": "explanation_of_formula",
                "describes": ["concept1", "concept2", ...]
            }},
            ...
        ],
        "poetry": [
            {{
                "content": "Original poetry text",
                "language": "Language of the original text",
                "translation": "English translation if applicable",
                "source": "Book title or source of the poetry",
                "poet": "Name of the poet",
                "related_concepts": ["concept1", "concept2", ...],
                "appearing_in": "book_title"
            }},
            ...
        ],
        "claims": [
            {{
                "content": "Claim content",
                "source": "Book title or other source",
                "confidence": 0.8,
                "timestamp": "YYYY-MM-DDTHH:MM:SS",
                "about_entity": "entity_name",
                "supports_concept": "concept_name",
                "contradicts": ["conflicting_claim_content1", "conflicting_claim_content2"]
            }},
            ...
        ]
    }}

    When processing the book chapters, please adhere to the following definitions:

        1. Stories: Overarching narratives or themes that span multiple events. They should have a name, description, version, and a list of event names that make up the story.

        2. Events: Specific occurrences with a definite time and place. They should have:
        - A name describing the event
        - A detailed description
        - A start date (in YYYY-MM-DD format)
        - An end date (in YYYY-MM-DD format)
        - Date precision (DAY, MONTH, YEAR, DECADE, or CENTURY)
        - Involved entities (people, organizations, or places directly involved)
        - Related concepts (ideas or theories relevant to the event)
        - The name of the next chronological event

        3. Entities: Specific people, organizations, or places mentioned in the text. They should have:
        - A name
        - A type (person, organization, or place)
        - A description
        - A language (usually 'en' for English)
        - Related entities (if any) with their relationship type and description

        4. Concepts: Abstract ideas, theories, or phenomena discussed in the text. They should have:
        - A name
        - A detailed description
        - A language (usually 'en' for English)

        5. Concept Relationships: Connections between different concepts. They should have:
        - The name of the concept it's coming from
        - The name of the concept it's going to
        - The type of relationship (e.g., "causes", "influences", "contradicts", "exemplifies")
        - The strength of the relationship (0.0 to 1.0)
        - The context in which this relationship is discussed
        - Whether the relationship is bidirectional

        6. Mathematical Formulas: Any mathematical equations or formulas mentioned. They should have:
        - A name
        - The formula itself
        - A description of what it represents
        - The concepts it describes

        7. Poetry: Poetic content mentioned in the text. They should have:
        - The original content of the poem
        - The language of the original text
        - An English translation (if applicable)
        - The source or book title where the poetry appears
        - The name of the poet
        - Related concepts (ideas or themes expressed in the poem)
        - The book title in which the poetry appears

        8. Claims: Statements or assertions made in the text. They should have:
        - The content of the claim
        - The source of the claim (usually the book title)
        - A confidence score (0.0 to 1.0) indicating how certain the claim is presented
        - A timestamp (if available, otherwise use the book's publication date)
        - The entity or concept the claim is about
        - The concept the claim supports (if applicable)
        - Any contradicting claims (if present in the text)

    Chapter heading: {heading}
    Chapter content: {content}
    """

    # First, try with GPT-4 API
    result = await safe_api_call(gpt4_api, prompt, system_prompt)
    
    # If GPT-4 API fails, retry with Anthropic API
    if result is None:
        logger.warning(f"API failed for chapter '{heading}'. Retrying with another API.")
        result = await safe_api_call(anthropic_api, prompt, system_prompt)
    
    # If both APIs fail, try splitting the content and retrying
    if result is None:
        logger.warning(f"Both APIs failed for chapter '{heading}'. Attempting to split content and retry.")
        split_contents = split_into_chunks(content, min_size=2500, max_size=3500)
        combined_result = {"stories": [], "events": [], "entities": [], "concepts": [], "concept_relationships": [], "mathematical_formulas": [], "poetry": [], "emotional_states": [], "claims": []}
        
        for i, split_content in enumerate(split_contents):
            split_prompt = prompt.replace(content, split_content)
            split_result = await safe_api_call(gpt4_api, split_prompt, system_prompt)
            
            if split_result is None:
                split_result = await safe_api_call(anthropic_api, split_prompt, system_prompt)
            
            if split_result:
                for key in combined_result.keys():
                    if key in split_result:
                        combined_result[key].extend(split_result[key])
            else:
                logger.error(f"Failed to process split {i+1}/{len(split_contents)} of chapter '{heading}'")
        
        if any(combined_result.values()):
            result = combined_result
        else:
            logger.error(f"Failed to process chapter '{heading}' even after splitting content.")
    
    return result

async def safe_api_call(api, prompt, system_prompt=None):
    """
    Make an async API call with error handling.
    """
    full_response = ""
    try:
        if api.provider == "anthropic":
            # For Anthropic, we need to adjust the input format
            response_generator = api.generate_text(prompt, system_prompt=system_prompt)
        else:
            response_generator = api.generate_text(prompt, system_prompt=system_prompt)
        
        async for chunk in response_generator:
            full_response += chunk
        
        # Check if the response is already a valid JSON string
        try:
            json_response = json.loads(full_response)
            return json_response
        except json.JSONDecodeError:
            # If it's not valid JSON, try to extract JSON from the response
            json_start = full_response.find('{')
            json_end = full_response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_string = full_response[json_start:json_end]
                return json.loads(json_string)
            else:
                raise ValueError("No valid JSON found in the response")
    except Exception as e:
        logger.error(f"API call failed: {str(e)}\nRaw response: {full_response}")
        return None

def find_related_concepts(session, concept_name, min_strength=0.5):
    query = """
    MATCH (c:Concept {name: $concept_name})-[r:RELATES_TO]-(related:Concept)
    WHERE r.strength >= $min_strength
    RETURN related.name AS related_concept, r.type AS relationship_type, r.strength AS strength
    ORDER BY r.strength DESC
    """
    return session.run(query, concept_name=concept_name, min_strength=min_strength)

def find_concept_clusters(session, min_strength=0.7):
    query = """
    CALL gds.graph.project(
        'conceptGraph',
        'Concept',
        {
            RELATES_TO: {
                properties: 'strength'
            }
        }
    )
    YIELD graphName

    CALL gds.louvain.stream('conceptGraph', {
        relationshipWeightProperty: 'strength'
    })
    YIELD nodeId, communityId

    WITH gds.util.asNode(nodeId) AS node, communityId
    RETURN communityId, collect(node.name) AS concepts
    ORDER BY size(concepts) DESC
    """
    return session.run(query)

async def process_book(book_name):
    logger.info(f"Processing book: {book_name}")
    
    try:
        # Set up directory structure
        base_dir = Path("data")
        summaries_dir = base_dir / "summaries"
        metadata_dir = base_dir / "metadata" / book_name
        summaries_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Load and preprocess the book content
        content = load_book_content(book_name)
        if not content:
            logger.error(f"Failed to load content for book: {book_name}")
            return
        
        preprocessed_content = preprocess_text(content)

        # Check if summary exists, if not, create it
        summary_file = summaries_dir / f"{book_name}_summary.json"
        if summary_file.exists():
            logger.info(f"Summary already exists for book: {book_name}")
            with open(summary_file, 'r') as f:
                book_info = json.load(f)
        else:
            logger.info(f"Generating summary for book: {book_name}")
            book_info = await extract_book_info(preprocessed_content, book_name)
            if not book_info:
                logger.error(f"Failed to extract book information for: {book_name}")
                return
            with open(summary_file, 'w') as f:
                json.dump(book_info, f, indent=2)

        # Process each chapter
        chapters = split_by_markdown_headings(preprocessed_content)
        total_chapters = len(chapters)
        
        for chapter_index, (heading, chapter_content) in enumerate(chapters, 1):
            chapter_dir = metadata_dir / f"chapter_{chapter_index}"
            chapter_dir.mkdir(exist_ok=True)
            
            # Split chapter into chunks
            chunks = split_into_chunks(chapter_content, min_size=6000, max_size=10000)
            total_chunks = len(chunks)
            
            for chunk_index, chunk in enumerate(chunks, 1):
                chunk_file = chapter_dir / f"chunk_{chunk_index}.json"
                chunk_text_file = chapter_dir / f"chunk_{chunk_index}.txt"
                error_file = chapter_dir / f"chunk_{chunk_index}_error.log"
                
                # Write the text chunk to a .txt file
                if not chunk_text_file.exists():
                    with open(chunk_text_file, 'w', encoding='utf-8') as f:
                        f.write(chunk)
                
                if chunk_file.exists():
                    logger.info(f"Skipping already processed chunk {chunk_index}/{total_chunks} of chapter {chapter_index}/{total_chapters}: {heading}")
                    continue
                
                logger.info(f"Processing chunk {chunk_index}/{total_chunks} of chapter {chapter_index}/{total_chapters}: {heading}")
                try:
                    chunk_analysis = await analyze_chapter(heading, chunk, book_name)
                    if chunk_analysis:
                        with open(chunk_file, 'w') as f:
                            json.dump(chunk_analysis, f, indent=2)
                    else:
                        raise Exception("Failed to analyze chunk")
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_index}/{total_chunks} of chapter {chapter_index}/{total_chapters} '{heading}' in book '{book_name}': {str(e)}")
                    with open(error_file, 'w') as f:
                        f.write(f"Error processing chunk: {str(e)}\n{traceback.format_exc()}")
        
        logger.info(f"Successfully processed all {total_chapters} chapters for: {book_name}")
        
    except Exception as e:
        logger.error(f"Error processing book {book_name}: {str(e)}\n{traceback.format_exc()}")

def split_into_chunks(text, min_size=15000, max_size=30000):
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) > max_size and len(current_chunk) >= min_size:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n\n'
        else:
            current_chunk += paragraph + '\n\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def add_missing_txt_files(book_name):
    base_dir = Path("data")
    metadata_dir = base_dir / "metadata" / book_name
    
    for chapter_dir in metadata_dir.glob("chapter_*"):
        for json_file in chapter_dir.glob("chunk_*.json"):
            txt_file = json_file.with_suffix('.txt')
            if not txt_file.exists():
                # Extract the chunk number from the filename
                chunk_number = int(json_file.stem.split('_')[1])
                
                # Load the original content and split it into chunks
                content = load_book_content(book_name)
                preprocessed_content = preprocess_text(content)
                chapters = split_by_markdown_headings(preprocessed_content)
                chapter_content = chapters[int(chapter_dir.name.split('_')[1]) - 1][1]
                chunks = split_into_chunks(chapter_content, min_size=6000, max_size=10000)
                
                # Write the corresponding chunk to the txt file
                if chunk_number <= len(chunks):
                    with open(txt_file, 'w', encoding='utf-8') as f:
                        f.write(chunks[chunk_number - 1])
                    logger.info(f"Created missing txt file: {txt_file}")
                else:
                    logger.warning(f"Chunk number {chunk_number} exceeds available chunks for {json_file}")

# Add this to your main function or create a new one to run it
async def update_existing_books():
    book_names = get_all_book_names()
    for book_name in book_names:
        add_missing_txt_files(book_name)

async def main():
    await update_existing_books()
    book_names = get_all_book_names()
    for book_name in book_names:
        await process_book(book_name)

if __name__ == "__main__":
    asyncio.run(main())