import { generateText } from './aiService';
import { computeQueryEmbedding } from './embeddingService';
import { getRelevantEventsAndClaims, getRelevantConceptRelationships } from './neo4jService';
import { Integer } from 'neo4j-driver';

export async function processChainOfThoughtQuestion(
  question: string,
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number; concept_relationships: number },
  reasoningTypes: string[],
  session: any // Pass the session as a parameter
): Promise<string> {
  if (typeof question !== 'string') {
    throw new Error(`Invalid question type: ${typeof question}. Expected a string.`);
  }

  console.info(`Starting to process chain-of-thought question: ${question}`);

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

  let context = `You think of the following question: ${question}\n`;
  /* context += `Apply ${reasoningTypes.join(', ')} reasoning using the following knowledge:\n`; */
  context += `Your mind retrieves the following information from your long term memory:\n`;

  try {
    const questionEmbedding = await computeQueryEmbedding(question);
    console.debug(`Computed question embedding for: ${question}`);

    const { events, claims } = await getRelevantEventsAndClaims(
      questionEmbedding,
      idealMix.events,
      idealMix.claims_ideas,
      0.3, // similarityThreshold, you may want to make this configurable
      queryDateRange
      // Removed session parameter
    );

    console.debug(`Retrieved ${events.length} events and ${claims.length} claims for question: ${question}`);

    const conceptRelationships = await getRelevantConceptRelationships(
      questionEmbedding,
      Integer.fromNumber(idealMix.concept_relationships),
      0.3
    );

    // Add concept relationships to context
    context += "It reminds you of the following concepts and relationships between them:\n";
    for (const relationship of conceptRelationships.relationships) {
      context += `${relationship.source} ${relationship.type} ${relationship.target}\n`;
    }
    context += "\n";
    // Add events to context
    context += "It reminds you of the following events:\n";
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
    context += "It reminds you of the following ideas you read about in books:\n";
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

    context += `\n
      You have been given the following instructions:
        1. Analyze the following question: ${question}.
        2. Use deductive, inductive, abductive, analogical, or causal reasoning in your analysis. 
        3. Answer the question using up to two Mermaid diagrams of your choice.
        4. Do not use parentheses, curly braces, square brackets, and percentage signs in node labels, as these characters are not supported by the Mermaid parser.
        5. Accompany each diagram with a clear, concise explanation of the visualized reasoning.
    `;

    // Sanitize and encode the context and system prompt
    console.log('Debug: Context before sanitization:', context);
    console.log('Debug: System prompt before sanitization:', systemPrompt);

    const sanitizedContext = sanitizeString(context);
    const sanitizedSystemPrompt = sanitizeString(systemPrompt);

    console.log('Debug: Sanitized context:', sanitizedContext);
    console.log('Debug: Sanitized system prompt:', sanitizedSystemPrompt);

    const formattedContext = `Question: ${sanitizeString(question)}\n\nContext:\n${sanitizeString(context)}`;
    const formattedSystemPrompt = sanitizeString(systemPrompt);

    let response = '';
    try {
      for await (const chunk of generateText(
        formattedContext,
        formattedSystemPrompt,
        'anthropic',
        'claude-3-5-sonnet-20240620'
      )) {
        response += chunk;
      }
    } catch (generateTextError) {
      console.error('Error during generateText call:', generateTextError);
      console.log('Debug: Full error object:', JSON.stringify(generateTextError, null, 2));
      throw new Error('Failed to generate text response.');
    }

    console.info(`Finished processing chain-of-thought question: ${question}`);
    return `\n## ${question}\n\n${response}\n`;
  } catch (error) {
    console.error(`Error processing chain-of-thought question: ${question}`, error);
    throw error; // Ensure the error is propagated
  }
}

// Add this helper function at the end of the file
function sanitizeString(input: string): string {
  // Remove any non-printable characters except newlines and tabs
  const sanitized = input.replace(/[^\x20-\x7E\x0A\x09]/g, '');
  
  // Replace any sequences of whitespace (including newlines) with a single space
  return sanitized.replace(/\s+/g, ' ').trim();
}