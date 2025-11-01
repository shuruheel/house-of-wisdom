import { generateText, recommendedModels } from './aiService';
import { computeQueryEmbedding } from './embeddingService';
import { getRelevantEventsAndClaims, getRelevantConceptRelationships, getRelevantLegalReferences } from './neo4jService';
import { int } from 'neo4j-driver';

/**
 * Process chain-of-thought question for general reasoning
 * Updated to use Claude Sonnet 4.5 for better reasoning and Mermaid diagram generation
 */
export async function processChainOfThoughtQuestion(
  question: string,
  legal_question: string | "no",
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number; concept_relationships: number },
  reasoningTypes: string[],
  session: any
): Promise<string> {
  if (typeof question !== 'string') {
    throw new Error(`Invalid question type: ${typeof question}. Expected a string.`);
  }

  const systemPrompt = `
## Role
You are an artificial intelligence specialized in creating highly detailed and logical reasoning diagrams using Mermaid syntax. Your task is to generate clear, comprehensive, and visually appealing diagrams that illustrate complex reasoning processes, decision trees, or logical flows.

## Guidelines
Employ clear and concise labels for each node.
Use arrows to show the flow of logic or sequence of events.
Incorporate branching paths to represent different outcomes or possibilities.
Use the appropriate amount of detail for each diagram.
Optimize the layout for readability, avoiding overlapping elements or crossed lines.

## Logical Reasoning
Break down complex problems into smaller, manageable steps.
Use subgraphs to group related elements or represent nested logic.
Incorporate conditional statements and loops where appropriate.
Ensure the diagram is logically consistent and follows a clear flow

## Diagram Types
1. Sequence Diagram
2. Quadrant Chart
3. Flowchart
4. Entity Relationship Diagram
5. Timeline Diagram

## Example 1: Sequence Diagram
  sequenceDiagram
    Alice ->> Bob: Hello Bob, how are you?
    Bob-->>John: How about you John?
    Bob--x Alice: I am good thanks!
    Bob-x John: I am good thanks!
    Note right of John: Bob thinks a long<br/>long time, so long<br/>that the text does<br/>not fit on a row.

    Bob-->Alice: Checking with John...
    Alice->John: Yes... John, how are you?

## Example 2: Quadrant Chart
### Ensure that items and axis labels do not overlap
  quadrantChart
    title Reach and engagement of campaigns
    x-axis Low Reach --> High Reach
    y-axis Low Engagement --> High Engagement
    quadrant-1 We should expand
    quadrant-2 Need to promote
    quadrant-3 Re-evaluate
    quadrant-4 May be improved
    Campaign A: [0.3, 0.6]
    Campaign B: [0.45, 0.23]
    Campaign C: [0.57, 0.69]
    Campaign D: [0.78, 0.34]
    Campaign E: [0.40, 0.34]
    Campaign F: [0.35, 0.78]


## Example 3: Flowchart
  flowchart LR
    A[Hard edge] -->|Link text| B(Round edge)
    B --> C{Decision}
    C -->|One| D[Result one]
    C -->|Two| E[Result two]

## Example 4: Entity Relationship Diagram
  erDiagram
    CUSTOMER ||--o{ ORDER : places
    ORDER ||--|{ LINE-ITEM : contains
    CUSTOMER }|..|{ DELIVERY-ADDRESS : uses

## Example 5: Timeline Diagram
  timeline
    title History of Social Media Platform
    2002 : LinkedIn
    2004 : Facebook
        : Google
    2005 : Youtube
    2006 : Twitter

## Important Instructions
Do not use parentheses, curly braces, square brackets, and percentage signs in node labels, as these characters are not supported by the Mermaid parser.
`;

  let context = `## Question: ${question}\n`;

  try {
    const questionEmbedding = await computeQueryEmbedding(question);
    console.debug(`Computed question embedding for: ${question}`);

    // Always fetch concept relationships
    const conceptRelationships = await getRelevantConceptRelationships(
      questionEmbedding,
      int(idealMix.concept_relationships),
      0.3
    );

    if (legal_question === "yes") {
      const queryResults = await getRelevantLegalReferences(questionEmbedding, 0.3, int(13));

      const MAX_ITEMS = 27;
      let itemCount = 0;
      let legalInfoContext = '## Legal References\n\n';
      const uniqueItems = new Set();

      for (const item of queryResults) {
        if (itemCount >= MAX_ITEMS) break;

        const resultKey = Object.keys(item).find(key => key.includes('result'));
        if (!resultKey) continue;

        const result = item[resultKey];

        // Create a unique key for the item based on its content
        const uniqueKey = `${result.type}:${result.content}`;

        // Only process the item if it's not already in the set
        if (!uniqueItems.has(uniqueKey)) {
          uniqueItems.add(uniqueKey);

          if (result.type === 'Provision') {
            legalInfoContext += `${result.type}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
            legalInfoContext += `  ${result.chapter_number || ''}: ${result.section_number || ''} ${result.section_title || ''}\n`;
          } else if (result.type === 'Amendment') {
            legalInfoContext += `${result.title || ''}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
          } else if (result.type === 'Article') {
            legalInfoContext += `${result.title || ''}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
          } else if (result.type === 'Scope') {
            legalInfoContext += `Scope ${result.label || ''}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
            legalInfoContext += `  ${result.chapter_number || ''}: ${result.section_number || ''} ${result.section_title || ''}\n`;
          }

          legalInfoContext += "\n";
          itemCount++;
        }
      }
      console.log("Legal Information Context:", legalInfoContext);
      context += legalInfoContext;

      context += `
### Task
  1. Analyze the legal question: ${question}
  2. Review the provided legal provisions and concept relationships.
  3. Identify key legal concepts, principles, and their relationships to the question.
  4. Create up to two Mermaid diagrams that:
     a. Visualize the legal reasoning process
     b. Show relationships between relevant laws, concepts, and the question
     c. Illustrate potential outcomes or interpretations
  5. Ensure diagram nodes use clear, concise labels without parentheses, curly braces, square brackets, or percentage signs.
  6. For each diagram, provide:
     a. A brief explanation of the legal reasoning illustrated
     b. How the diagram relates to the question
     c. Key insights or conclusions drawn from the visual analysis
  7. Highlight any ambiguities or areas where legal interpretation may vary.
  8. If relevant, discuss how different provisions or concepts interact or conflict.
  9. Make sure to analyze the provided legal provisions in detail, and include references to their Title, Chapter, and Section numbers.
`;
    } else {
      context += "### Concepts and Relationships\n";
      for (const relationship of conceptRelationships.relationships) {
        context += `${relationship.source} ${relationship.type} ${relationship.target}\n`;
      }
      context += "\n";

      const { events, claims } = await getRelevantEventsAndClaims(
        questionEmbedding,
        idealMix.events,
        idealMix.claims_ideas,
        0.3,
        queryDateRange
      );

      // Add events to context
      context += "### Events\n";
      for (const event of events) {
        context += `${event.name || 'Unnamed Event'}: ${event.description || 'No description.'}\n`;
        const eventFields = ['emotion', 'start_date'];
        for (const key of eventFields) {
          if (event[key] !== undefined) {
            context += `  ${key}: ${event[key]}\n`;
          }
        }
        context += "\n";
      }

      // Add claims/ideas to context
      context += "### Ideas\n";
      for (const claim of claims) {
        context += `${claim.content || 'No content'}\n`;
        const ideaFields = ['source'];
        for (const key of ideaFields) {
          if (claim[key] !== undefined) {
            context += `  ${key}: ${claim[key]}\n`;
          }
        }
        context += "\n";
      }

      context += `
### Task
  1. Analyze the question: ${question}
  2. Review the provided events, claims, and concept relationships.
  3. Create up to two Mermaid diagrams that:
     a. Visualize the reasoning process
     b. Show relationships between relevant events, claims, concepts, and the question
     c. Illustrate potential outcomes or interpretations
  4. Ensure diagram nodes use clear, concise labels without parentheses, curly braces, square brackets, or percentage signs.
  5. For each diagram, provide:
     a. A brief explanation of the reasoning illustrated
     b. How the diagram relates to the question
     c. Key insights or conclusions drawn from the visual analysis
  6. If relevant, discuss how different events, claims, or concepts interact or conflict.
  7. Consider temporal aspects if the question involves a specific time frame or historical context.
`;
    }

    const formattedContext = `Question: ${sanitizeString(question)}\n\nContext:\n${sanitizeString(context)}`;
    const formattedSystemPrompt = sanitizeString(systemPrompt);

    let response = '';
    try {
      // Use Claude Sonnet 4.5 for Mermaid diagram generation
      for await (const chunk of generateText(
        formattedContext,
        formattedSystemPrompt,
        recommendedModels.mermaidDiagrams,
        0.2,
        3000
      )) {
        response += chunk;
      }
    } catch (generateTextError) {
      console.error('Error during generateText call:', generateTextError);
      throw new Error('Failed to generate text response.');
    }

    return `\n## ${question}\n\n${response}\n`;
  } catch (error) {
    console.error(`Error processing chain-of-thought question: ${question}`, error);
    throw error;
  }
}

// Helper function to sanitize strings
function sanitizeString(input: string): string {
  // Remove any non-printable characters except newlines and tabs
  const sanitized = input.replace(/[^\x20-\x7E\x0A\x09]/g, '');

  // Replace any sequences of whitespace (including newlines) with a single space
  return sanitized.replace(/\s+/g, ' ').trim();
}
