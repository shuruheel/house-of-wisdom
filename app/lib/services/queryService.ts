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
      # Role
      You are an AI specialized in comprehensive analysis and chain-of-thought reasoning.

      # Task
      1. Extract and categorize key information from queries
      2. Break down complex queries into logical steps
      3. Generate insightful questions to guide reasoning
      4. Apply various reasoning types appropriately

      # Principles
      - Be precise, concise, and thorough in your analysis
      - Ensure extracted information is directly relevant to the query
      - Formulate questions that promote deep, multi-faceted thinking
      - Match reasoning types accurately to each generated question
    `;

    const prompt = `
      Analyze the following query: ${query}

      Extract and categorize key information:
        a) Entities: Specific people, places, organizations, or tangible objects
        b) Concepts: Abstract ideas, themes, or intangible notions
        c) Time references: Specific dates, periods, or temporal contexts

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
    for await (const chunk of generateText(prompt, systemPrompt, 'openai', 'gpt-4o')) {
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