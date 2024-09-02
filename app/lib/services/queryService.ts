import { generateText } from './aiService';
import { handleError } from '../utils/errorHandler';
import { RateLimiter } from 'limiter';

const limiter = new RateLimiter({ tokensPerInterval: 5, interval: 'minute' });

interface QueryElements {
  key_entities: string[];
  key_concepts: string[];
  time_reference: string | null;
  chain_of_thought_questions: {
    question: string;
    reasoning_types: string[];
  }[];
  ideal_mix: {
    events: number;
    claims_ideas: number;
    chunks: number;
  };
}

export async function extractQueryElements(query: string): Promise<QueryElements> {
  try {
    await limiter.removeTokens(1);
    const systemPrompt = `
      You are an AI specialized in chain-of-thought reasoning. 
      You extract key entities, concepts, and time references from the query.
      You break down queries into smaller steps and questions covering types of reasoning (deductive, inductive, abductive, or abstract).
      Be precise and concise in your extractions.
    `;

    const prompt = `
      Analyze the following query: ${query}

      Please extract the following from the query:
      1. Entities (specific people, places, organizations)
      2. Concepts (abstract ideas or themes), including those mentioned in the chain-of-thought reasoning questions
      3. Time period or date reference (if mentioned)

      Please generate a list of 3-5 chain-of-thought questions that would help respond to the query, with not more than one entity per question. For each question, specify the type(s) of reasoning best suited to answer the question (e.g. deductive, inductive, abductive, or abstract).

      Format the response as a JSON object with the following structure:
          {
              "key_entities": ["entity1", "entity2", ...],
              "key_concepts": ["concept1", "concept2", ...],
              "time_reference": "string or null",
              "chain_of_thought_questions": [
                  {
                      "question": "...",
                      "reasoning_types": ["deductive", "inductive"]
                  },
                  {
                      "question": "...",
                      "reasoning_types": ["abductive"]
                  }
              ]
          }

      IMPORTANT: Return ONLY a complete JSON object, without any additional text or explanation.
    `;

    let fullResponse = '';
    for await (const chunk of generateText(prompt, systemPrompt, 'anthropic', 'claude-3-5-sonnet-20240620')) {
      fullResponse += chunk;
    }

    const cleanedResponse = fullResponse.trim().replace(/```json|```/g, '');
    const elements = JSON.parse(cleanedResponse) as QueryElements;

    // Ensure all expected keys are present
    elements.key_entities = elements.key_entities || [];
    elements.key_concepts = elements.key_concepts || [];
    elements.time_reference = elements.time_reference || null;
    elements.chain_of_thought_questions = elements.chain_of_thought_questions || [];

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
        chunks: 3
      };
    }

    return elements;
  } catch (error) {
    console.error('Failed to parse LLM response as JSON:', error);
    return {
      key_entities: [],
      key_concepts: [],
      time_reference: null,
      chain_of_thought_questions: [],
      ideal_mix: {
        events: 27,
        claims_ideas: 27,
        chunks: 3
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