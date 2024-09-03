import { generateText } from './aiService';
import { computeQueryEmbedding } from './embeddingService';
import { getDriver, getRelevantEventsAndClaims } from './neo4jService';
import { Event, Claim } from '../../types';

export async function processChainOfThoughtQuestion(
  question: string,
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number },
  conceptRelationships: any[],
  reasoningTypes: string[],
  session: any // Pass the session as a parameter
): Promise<string> {
  if (typeof question !== 'string') {
    throw new Error(`Invalid question type: ${typeof question}. Expected a string.`);
  }

  console.info(`Starting to process chain-of-thought question: ${question}`);

  const systemPrompt = `
    # Role
    You are an artificial intelligence well-trained to apply reasoning to questions and visualize the reasoning using Mermaid diagrams. 

    # Guidelines
    Use appropriate shapes for different elements.
    Employ clear and concise labels for each node.
    Use arrows to show the flow of logic or sequence of events.
    Incorporate branching paths to represent different outcomes or possibilities.
    Use color coding to depict emotions. 

    Which of the following types of diagrams best capture your thinking regarding the question? 

    # Example: Sequence Diagram
    sequenceDiagram
    Alice->>John: Hello John, how are you?
    John-->>Alice: Great!
    Alice-)John: See you later!

    # Example: Flowchart
    flowchart LR
    A[Hard edge] -->|Link text| B(Round edge)
    B --> C{Decision}
    C -->|One| D[Result one]
    C -->|Two| E[Result two]

    # Example: Quadrant Chart
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

    # Example: Mind Map
    mindmap
      root((mindmap))
        Origins
          Long history
          ::icon(fa fa-book)
          Popularisation
            British popular psychology author Tony Buzan
        Research
          On effectiveness<br/>and features
          On Automatic creation
            Uses
                Creative techniques
                Strategic planning
                Argument mapping
        Tools
          Pen and paper
          Mermaid

    # Important Instructions
    Do not use parentheses, curly braces, square brackets, and percentage signs in node labels, as these characters are not supported by the Mermaid parser.
  `;

  let context = `## Question: ${question}\n`;
  context += `Apply ${reasoningTypes.join(', ')} reasoning using the following knowledge:\n`;

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

    // Add concept relationships to the context
    context += "##  Semantic Map\n\n";
    if (conceptRelationships.length > 0) {
      for (const relationship of conceptRelationships) {
        context += `${relationship.source} ${relationship.type} ${relationship.target}.\n`;
      }
    } else {
      context += "No relevant concept relationships found.\n";
    }

    context += `\n
      # Your Task
        1. Analyze the following question using the provided knowledge: ${question}.
        2. Apply the specified reasoning types to the question and knowledge: ${reasoningTypes.join(', ')}.
        3. Determine the best type of Mermaid diagrams to visualize your thinking (refer to given Examples). 
        4. Generate a Mermaid diagram appropraite for each type of reasoning.
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
        'openai',
        'gpt-4o-mini'
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