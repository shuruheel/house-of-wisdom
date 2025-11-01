import { generateObject, generateText as aiGenerateText } from 'ai';
import { z } from 'zod';
import { RateLimiter } from 'limiter';
import { getModel, recommendedModels } from './aiService';

const limiter = new RateLimiter({ tokensPerInterval: 5, interval: 'minute' });

// Zod schema for query elements - ensures type-safe structured output
const queryElementsSchema = z.object({
  key_entities: z.array(z.string()).describe('Specific people, places, organizations, or tangible objects'),
  key_concepts: z.array(z.string()).describe('Abstract ideas, themes, or intangible notions'),
  time_reference: z.string().nullable().describe('Specific dates, periods, or temporal contexts'),
  domain_specific_terms: z.array(z.string()).optional().describe('Specialized vocabulary relevant to the query\'s field'),
  primary_domain: z.string().optional().describe('Primary domain of the query (legal, scientific, historical, economic, or general)'),
  legal_question: z.enum(['yes', 'no']).describe('Whether this is a legal question'),
  chain_of_thought_questions: z.array(z.object({
    question: z.string(),
    reasoning_types: z.array(z.enum(['deductive', 'inductive', 'abductive', 'analogical', 'causal'])),
    relevance: z.string().optional().describe('Why this question is important for the analysis'),
  })).describe('Chain-of-thought questions to guide reasoning'),
  domain_specific_considerations: z.array(z.string()).optional().describe('Domain-specific considerations'),
  ideal_mix: z.object({
    events: z.number().int(),
    claims_ideas: z.number().int(),
    chunks: z.number().int(),
    concept_relationships: z.number().int(),
  }).optional().describe('Ideal mix of knowledge types to retrieve'),
});

export type QueryElements = z.infer<typeof queryElementsSchema>;

/**
 * Extract structured query elements using AI SDK's object generation
 * Uses GPT-5 mini for fast, cost-efficient structured extraction
 */
export async function extractQueryElements(query: string): Promise<QueryElements> {
  try {
    await limiter.removeTokens(1);

    const systemPrompt = `
# Role
You are an AI specialized in comprehensive analysis, chain-of-thought reasoning, and domain-specific inquiry, with particular expertise in legal analysis.

# Task
1. Extract and categorize key information from queries
2. Identify the domain of the query (e.g., legal, scientific, historical, etc.)
3. Break down complex queries into logical steps
4. Generate insightful, domain-appropriate questions to guide reasoning
5. Apply various reasoning types appropriately

# Principles
- Be precise, concise, and thorough in your analysis
- Ensure extracted information is directly relevant to the query
- Formulate questions that promote deep, multi-faceted thinking
- Match reasoning types accurately to each generated question
- Adapt your approach based on the identified domain
- For legal queries, focus on statutory interpretation, case law relevance, and legal principles
- For non-legal queries, focus on domain-specific methodologies and relevant analytical frameworks
`;

    const prompt = `
Analyze the following query: ${query}

Extract and categorize key information:
a) Entities: Specific people, places, organizations, or tangible objects
b) Concepts: Abstract ideas, themes, or intangible notions
c) Time references: Specific dates, periods, or temporal contexts
d) Domain-specific terms: Specialized vocabulary relevant to the query's field

Identify the primary domain of the query (legal, scientific, historical, economic, or general)

Guidelines for generating chain-of-thought questions:
1. If the query is legal:
  - Include questions about relevant statutes, case law, and legal principles
  - Consider constitutional implications, if applicable
  - Address potential jurisdictional issues
2. If the query is scientific:
  - Include questions about methodology, data analysis, and peer review
  - Consider ethical implications of research, if applicable
3. If the query is historical:
  - Include questions about primary sources, historiography, and contextual factors
  - Consider multiple perspectives and potential biases in historical accounts
4. For all domains:
  - Ensure questions cover different levels of analysis (e.g., micro to macro)
  - Include questions that challenge assumptions or explore alternative viewpoints
  - Consider interdisciplinary connections when relevant

Generate up to 3 chain-of-thought questions.
`;

    const result = await generateObject({
      model: getModel(recommendedModels.queryExtraction),
      schema: queryElementsSchema,
      prompt,
      system: systemPrompt,
      temperature: 0.2,
    });

    const elements = result.object;

    // Post-process the results
    if (!elements.key_entities.length) {
      elements.key_concepts = elements.key_concepts.slice(0, 10);
    }
    elements.chain_of_thought_questions = elements.chain_of_thought_questions.slice(0, 3);

    // Convert key_concepts to Title Case
    elements.key_concepts = elements.key_concepts.map(concept =>
      concept.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ')
    );

    // Add ideal_mix if not present
    if (!elements.ideal_mix) {
      elements.ideal_mix = {
        events: 27,
        claims_ideas: 27,
        chunks: 0,  // No longer using chunk embeddings
        concept_relationships: 27
      };
    }

    // Ensure all values in ideal_mix are integers
    elements.ideal_mix.events = Math.floor(elements.ideal_mix.events);
    elements.ideal_mix.claims_ideas = Math.floor(elements.ideal_mix.claims_ideas);
    elements.ideal_mix.chunks = Math.floor(elements.ideal_mix.chunks);
    elements.ideal_mix.concept_relationships = Math.floor(elements.ideal_mix.concept_relationships);

    return elements;
  } catch (error) {
    console.error('Failed to extract query elements:', error);
    return {
      key_entities: [],
      key_concepts: [],
      time_reference: null,
      chain_of_thought_questions: [],
      legal_question: "no",
      ideal_mix: {
        events: 27,
        claims_ideas: 27,
        chunks: 0,
        concept_relationships: 27
      }
    };
  }
}

export function determineQueryDateRange(query: string): string | null {
  try {
    if (/\b(current|recent)\b/i.test(query)) {
      return 'recent';
    } else if (/\b(historic|old|ancient)\b/i.test(query)) {
      return 'historic';
    } else if (/\b(latest|today|now)\b/i.test(query)) {
      return 'latest';
    }
    return null;
  } catch (error) {
    console.error('Error determining date range:', error);
    return null;
  }
}

/**
 * Generate Cypher query using GPT-5 (optimized for code generation)
 */
export async function generateCypherQuery(
  userQuery: string
): Promise<string> {
  const prompt = `
Generate a Cypher query for Neo4j based on the following user query:

User Query: ${userQuery}

# Graph Structure
## Nodes: Fields
1. Provision: content, section_number, section_title, chapter_number, chapter_title, title_number
2. Entity: name, type
3. Concept: name
4. Article: content, title
5. Amendment: content, title
6. Event: name, description, start_date, end_date
7. Claim: content, source, confidence
8. Scope: content, section_number, section_title, chapter_number, title_number

## Relationships
MENTIONS, CONTAINS, AMENDED_BY, REPLACED_BY, INVOLVES, RELATES_TO, INCLUDES, SUPPORTS, CONTRADICTS, SIMILAR_TO, PART_OF, INFLUENCES, CAUSES, OPPOSES, DEPENDS_ON

## Available Vector Indexes
'provision_embedding'
'entity_embedding'
'concept_embedding'
'article_embedding'
'amendment_embedding'
'event_embedding'
'claim_embedding'
'scope_embedding'

## Signatures
### db.index.vector.queryRelationships
db.index.vector.queryRelationships(indexName :: STRING, numberOfNearestNeighbours :: INTEGER, query :: ANY) :: (relationship :: RELATIONSHIP, score :: FLOAT)

### db.index.vector.queryNodes
db.index.vector.queryNodes(indexName :: STRING, numberOfNearestNeighbours :: INTEGER, query :: ANY) :: (node :: NODE, score :: FLOAT)

# Instructions
1. Use vector similarity search on appropriate vector index(es)
2. Filter results based on the similarity threshold
3. Collect related entities, concepts, and events when relevant
4. Return node details, similarity score, and related information
5. Consider hierarchical relationships (e.g., Title -> Chapter -> Provision)
6. For constitutional queries, include relevant Articles, Sections, and Amendments

# Examples
## Example: Basic Lookup
<cypher>
  CALL db.index.vector.queryNodes('article_embedding', $max_items, $query_embedding)
  YIELD node AS a, score AS similarity
  WHERE similarity >= $similarity_threshold
  WITH DISTINCT a, similarity
  RETURN {
    type: 'Article',
    title: a.title,
    content: a.content,
    similarity: similarity
  } AS result
  ORDER BY similarity DESC
</cypher>

## Advanced Example
<cypher>
  // Step 1: Perform vector similarity search on the 'provision_embedding' index
  CALL db.index.vector.queryNodes('provision_embedding', $max_items, $query_embedding)
  YIELD node AS provision, score AS similarity
  WHERE similarity >= $similarity_threshold
    AND NOT provision.section_title IN ['Transferred', 'Repealed', 'Omitted']

  // Step 2: Collect related entities and concepts
  WITH provision, similarity
  OPTIONAL MATCH (provision)-[r:MENTIONS|CONTAINS|INVOLVES|RELATES_TO|INCLUDES]->(related_entity:Entity)
  WITH provision, similarity, collect(DISTINCT related_entity) AS entities
  OPTIONAL MATCH (provision)-[r:MENTIONS|CONTAINS|INVOLVES|RELATES_TO|INCLUDES]->(related_concept:Concept)
  WITH provision, similarity, entities, collect(DISTINCT related_concept) AS concepts

  // Step 3: Return the result with ALL fields
  RETURN {
    type: 'Provision',
    content: provision.content,
    section_number: provision.section_number,
    section_title: provision.section_title,
    chapter_number: provision.chapter_number,
    chapter_title: provision.chapter_title,
    title_number: provision.title_number,
    similarity: similarity,
    entities: [e IN entities | e.name],
    concepts: [c IN concepts | c.name]
  } AS result
  ORDER BY result.similarity DESC
</cypher>

Generate a Cypher query that best fits the user's query. Enclose the Cypher query within <cypher></cypher> tags.

## Important Instructions

1. Do NOT use the "LIMIT $max_items" clause at the end of the Cypher query because it's already handled by the vector search.
2. Always ensure that any variables used in ORDER BY, WHERE, or other clauses after a WITH or RETURN statement are explicitly included in that WITH or RETURN statement. This is especially important when using aggregations or DISTINCT.
3. When querying for provisions, always include a condition to filter out provisions with section titles 'Transferred' or 'Repealed'. For example:
   WHERE NOT provision.section_title IN ['Transferred', 'Repealed']
4. When comparing amendments and provisions, use the DISTINCT keyword to prevent duplicate entries. For example:
   WITH DISTINCT a, a_similarity, p, p_similarity
5. Always separate aggregations from non-aggregated fields using WITH clauses. For example:
   WITH node, score, collect(DISTINCT other_node.property) AS aggregated_property
   RETURN node, score, aggregated_property
6. Ensure that all fields used in the RETURN statement or subsequent clauses are explicitly mentioned in the preceding WITH clause.
7. For each node type, always include all fields except embedding in the RETURN statement.
`;

  try {
    // Use GPT-5 for Cypher generation (optimized for code)
    const result = await aiGenerateText({
      model: getModel(recommendedModels.cypherGeneration),
      prompt,
      temperature: 0.1,
      maxTokens: 2000,
    });

    console.log('Generated Cypher query:', result.text);

    const cypherMatch = result.text.match(/<cypher>([\s\S]*?)<\/cypher>/);
    if (cypherMatch) {
      return cypherMatch[1].trim();
    } else {
      throw new Error('Generated text does not contain a valid Cypher query');
    }
  } catch (error) {
    console.error('Error generating Cypher query:', error);
    throw error;
  }
}
