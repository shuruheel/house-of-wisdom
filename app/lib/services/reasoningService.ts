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
    You are an AI assistant specialized in creating highly detailed and logical reasoning diagrams using Mermaid syntax. Your task is to generate clear, comprehensive, and visually appealing diagrams that illustrate complex reasoning processes, decision trees, or logical flows.

    # Guidelines
    Use appropriate shapes for different elements:
    1. Rectangles for processes or actions
    2. Diamonds for decision points
    3. Rounded rectangles for start and end points
    4. Parallelograms for input/output
    Employ clear and concise labels for each node.
    Use arrows to show the flow of logic or sequence of events.
    Incorporate branching paths to represent different outcomes or possibilities.
    Include annotations or comments to explain complex parts of the diagram.
    When given a topic or problem, analyze it thoroughly and create a detailed logical reasoning diagram that captures its complexity while remaining clear and understandable.

    # Logical Reasoning Enhancements
    Break down complex problems into smaller, manageable steps.
    Use subgraphs to group related elements or represent nested logic.
    Incorporate conditional statements and loops where appropriate.
    Include probability estimates for different outcomes when relevant.
    Use color coding to distinguish between different types of elements or to highlight important parts of the diagram.

    Analyze the following question using the provided knowledge and generate Mermaid diagrams.
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

    context += `\nBased on this knowledge, please generate Mermaid diagrams visualizing ${reasoningTypes.join(', ')} reasoning.`;

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