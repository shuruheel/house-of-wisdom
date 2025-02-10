import os
import json
import logging
import traceback
from pathlib import Path
from report_loader import load_report_content, get_all_report_names
from text_preprocessor import preprocess_text, split_by_sections
from api_wrapper import get_api
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize API clients
gemini_api = get_api("google", "gemini-1.5-pro-exp-0827", temperature=0.1)
gpt4_api = get_api("openai", "gpt-4o", temperature=0.1)  # Changed from "gpt-4o" to "gpt-4"
anthropic_api = get_api("anthropic", "claude-3-sonnet-20240320", temperature=0.1)  # Updated to the latest model
groq_api = get_api("groq", "llama-3.1-70b-versatile", temperature=0.1)

async def safe_api_call(api, prompt, system_prompt=None):
    """
    Make an API call with error handling, supporting async generators.
    """
    try:
        response_generator = api.generate_text(prompt)
        response = ""
        async for chunk in response_generator:
            response += chunk

        # Check if the response is already a valid JSON string
        try:
            json_response = json.loads(response)
            return json_response
        except json.JSONDecodeError:
            # If it's not valid JSON, try to extract JSON from the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_string = response[json_start:json_end]
                return json.loads(json_string)
            else:
                raise ValueError("No valid JSON found in the response")
    except Exception as e:
        logger.error(f"API call failed: {str(e)}\nRaw response: {response}")
        return None

# Modify the extract_report_info function to use the async safe_api_call
async def extract_report_info(content, report_name):
    """
    Use Google Gemini 1.5 Pro to extract report summary information.
    """
    prompt = f"""
    ## Objective
    Analyze the following report content and generate a brief summary highlighting key findings, methodologies, and conclusions. 

    ## IMPORTANT REQUIREMENTS
    Return a complete JSON object without any additional markdown or comments. 
    Make sure that the JSON object isn't truncated due to token limits. 
    Response should begin with {{ and end with }}.

    ## Response JSON Format
    {{
        "report": {{
            "title": "{report_name}",
            "summary": "brief_summary",
            "organization": "publishing_organization"
        }}
    }}

    ## Report Content
    {content}
    """
    
    return await safe_api_call(gemini_api, prompt)

async def analyze_section(heading, content, report_name):
    """
    Analyze a section of the report using the appropriate API based on content length.
    """
    prompt = f"""
    ## Objective
    Analyze the following section of the report titled "{report_name}" and provide information in a format suitable for a Neo4j graph database.
    Extract the most important Findings, Events, Entities, Concepts, Data Points, Methodologies, Recommendations, and Concept Relationships mentioned in the section. 

    ## IMPORTANT REQUIREMENTS
    Return a complete JSON object without any additional markdown or comments. 
    Make sure that the JSON object isn't truncated due to token limits. 
    Response should begin with {{ and end with }}.

    ## Neo4j Graph Database Structure
    CREATE 
    (:Report {{title: String, summary: String, organization: String}}),
    (:Story {{name: String, description: String, version: String}}),
    (:Claim {{content: String, source: String, confidence: Float}})
    (:Event {{
        name: String,
        description: String,
        start_date: Date,
        end_date: Date,
        date_precision: String  # 'DAY', 'MONTH', 'YEAR', 'DECADE', 'CENTURY'
    }}),
    (:Entity {{name: String, type: String, description: String}}),
    (:Concept {{name: String, description: String, language: String}}),
    (:DataPoint {{value: Float, unit: String, description: String}}),

    CREATE
    (:Report)-[:CONTAINS]->(:Story),
    (:Story)-[:CONTAINS]->(:Claim),
    (:Claim)-[:BASED_ON]->(:DataPoint),
    (:Event)-[:INVOLVES]->(:Entity),
    (:Event)-[:RELATES_TO]->(:Concept),
    (:Entity)-[:RELATES_TO {{type: String, description: String}}]->(:Entity),
    (:Concept)-[:RELATES_TO {{type: String, description: String}}]->(:Concept),

    ## Response JSON Format
    {{
        "claims": [
            {{
                "content": "Claim content",
                "source": "Organization or individual making the claim",
                "confidence": 0.8,
                "about_entity": "entity_name",
                "supports_concept": "concept_name",
                "contradicts": ["conflicting_claim_content1", "conflicting_claim_content2"]
            }},
            ...
        ],
        "data_points": [
            {{
                "name": "data_point_name",
                "description": "description_of_data_point",
                "value": 123.45,
                "unit": "unit_of_measurement"
                
            }},
            ...
        ],
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
                "related_concepts": ["concept1", "concept2", ...]
            }},
            ...
        ],
        "entities": [
            {{
                "name": "entity_name",
                "type": "person/organization/country/etc.",
                "description": "entity_description",
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
                "description": "concept_description"
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
                "bidirectional": true
            }},
            ...
        ]
    }}

    Section heading: {heading}
    Section content: {content}
    """

    # First, try with GPT-4 API
    result = await safe_api_call(gpt4_api, prompt)
    
    # If GPT-4 API fails, retry with Anthropic API
    if result is None:
        logger.warning(f"API failed for section '{heading}'. Retrying with another API.")
        result = await safe_api_call(anthropic_api, prompt)
    
    # If both APIs fail, try splitting the content and retrying
    if result is None:
        logger.warning(f"Both APIs failed for section '{heading}'. Attempting to split content and retry.")
        split_contents = split_into_chunks(content, min_size=3000, max_size=6000)
        combined_result = {"findings": [], "events": [], "entities": [], "concepts": [], "concept_relationships": [], "data_points": [], "methodologies": [], "recommendations": []}
        
        for i, split_content in enumerate(split_contents):
            split_prompt = prompt.replace(content, split_content)
            split_result = await safe_api_call(gpt4_api, split_prompt)
            
            if split_result is None:
                split_result = await safe_api_call(anthropic_api, split_prompt)
            
            if split_result:
                for key in combined_result.keys():
                    if key in split_result:
                        combined_result[key].extend(split_result[key])
            else:
                logger.error(f"Failed to process split {i+1}/{len(split_contents)} of section '{heading}'")
        
        if any(combined_result.values()):
            result = combined_result
        else:
            logger.error(f"Failed to process section '{heading}' even after splitting content.")
    
    return result

# Modify the process_report function to use asyncio
async def process_report(report_name):
    logger.info(f"Processing report: {report_name}")
    
    try:
        # Set up directory structure
        base_dir = Path("data")
        summaries_dir = base_dir / "summaries"
        metadata_dir = base_dir / "reports" / report_name
        summaries_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        # Load and preprocess the report content
        content = load_report_content(report_name)
        if not content:
            logger.error(f"Failed to load content for report: {report_name}")
            return
        
        preprocessed_content = preprocess_text(content)

        # Check if summary exists, if not, create it
        summary_file = summaries_dir / f"{report_name}_summary.json"
        if summary_file.exists():
            logger.info(f"Summary already exists for report: {report_name}")
            with open(summary_file, 'r') as f:
                report_info = json.load(f)
        else:
            logger.info(f"Generating summary for report: {report_name}")
            report_info = await extract_report_info(preprocessed_content, report_name)
            if not report_info:
                logger.error(f"Failed to extract report information for: {report_name}")
                return
            with open(summary_file, 'w') as f:
                json.dump(report_info, f, indent=2)

        # Split the entire preprocessed content into chunks
        chunks = split_into_chunks(preprocessed_content, min_size=6000, max_size=10000)
        total_chunks = len(chunks)
        
        for chunk_index, chunk in enumerate(chunks, 1):
            chunk_file = metadata_dir / f"chunk_{chunk_index}.json"
            chunk_text_file = metadata_dir / f"chunk_{chunk_index}.txt"
            error_file = metadata_dir / f"chunk_{chunk_index}_error.log"
            
            # Write the text chunk to a .txt file
            if not chunk_text_file.exists():
                with open(chunk_text_file, 'w', encoding='utf-8') as f:
                    f.write(chunk)
            
            if chunk_file.exists():
                logger.info(f"Skipping already processed chunk {chunk_index}/{total_chunks}")
                continue
            
            logger.info(f"Processing chunk {chunk_index}/{total_chunks}")
            try:
                chunk_analysis = await analyze_section(f"Chunk {chunk_index}", chunk, report_name)
                if chunk_analysis:
                    with open(chunk_file, 'w') as f:
                        json.dump(chunk_analysis, f, indent=2)
                else:
                    raise Exception("Failed to analyze chunk")
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_index}/{total_chunks} in report '{report_name}': {str(e)}")
                with open(error_file, 'w') as f:
                    f.write(f"Error processing chunk: {str(e)}\n{traceback.format_exc()}")
        
        logger.info(f"Successfully processed all {total_chunks} chunks for: {report_name}")
        
    except Exception as e:
        logger.error(f"Error processing report {report_name}: {str(e)}\n{traceback.format_exc()}")

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

# Modify the main function to use asyncio
async def main():
    report_names = get_all_report_names()
    for report_name in report_names:
        await process_report(report_name)

# Run the main function using asyncio
if __name__ == "__main__":
    asyncio.run(main())