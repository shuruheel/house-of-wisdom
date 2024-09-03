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
    You are an AI assistant specialized in ${reasoningTypes.join(', ')} reasoning.
    Analyze the following question using the provided knowledge and generate Mermaid diagrams for ${reasoningTypes.join(', ')} reasoning.
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

    context += `\nBased on this knowledge, please generate Mermaid diagrams for ${reasoningTypes.join(', ')} reasoning.`;

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