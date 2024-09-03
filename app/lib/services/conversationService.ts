import fs from 'fs/promises';
import path from 'path';
import { handleError } from '../utils/errorHandler';
import { extractQueryElements, determineQueryDateRange } from './queryService';
import { computeQueryEmbedding } from './embeddingService';
import { getRelevantEventsAndClaims, getRelevantConceptRelationships } from './neo4jService';
import { getRelevantChunks } from './embeddingService';
import { formatQueryWithContext } from './contextService';
import { generateText } from './aiService';

interface ConversationTurn {
  text: string;
  response: string;
}

const HISTORY_DIR = path.join(process.cwd(), 'conversation_histories');

export async function* processQuery(query: string, conversationHistory: ConversationTurn[]) {
  try {
    console.info(`Processing new user query: ${query}`);

    // Ensure conversationHistory is an array
    if (!Array.isArray(conversationHistory)) {
      conversationHistory = [];
    }

    // Extract query elements
    const queryElements = await extractQueryElements(query);
    const { key_entities, key_concepts, time_reference, chain_of_thought_questions, ideal_mix } = queryElements;

    // Determine query date range
    const queryDateRange = determineQueryDateRange(query);

    // Compute query embedding
    const queryEmbedding = await computeQueryEmbedding(query);

    // Get relevant events, claims, and concept relationships
    const { events, claims } = await getRelevantEventsAndClaims(
      queryEmbedding,
      ideal_mix.events,
      ideal_mix.claims_ideas,
      0.3,
      queryDateRange
    );

    const { concepts, relationships: conceptRelationships } = await getRelevantConceptRelationships(key_concepts);

    // Get relevant chunks
    const relevantChunks = await getRelevantChunks(query, ideal_mix.chunks);

    // Format query with context, now including conversationHistory
    console.info('Formatting query with context');
    const formattedQueryResult = await formatQueryWithContext(
      query,
      conversationHistory,
      events,
      claims,
      relevantChunks,
      chain_of_thought_questions,
      queryDateRange,
      ideal_mix,
      conceptRelationships
    );

    const { formattedQuery, mermaidDiagrams } = formattedQueryResult;

    console.info('Formatted query:', formattedQuery);

    // Generate response using AI service
    const systemPrompt = `
      You are an AI designed to embody knowledge. 
      Whenever a human being says something to you, you receive their words with relevant Events, Ideas, and Structured Information from your mind. 
      You have this relevant knowledge. It does not come from outside. 
      You have a unique ability to process large amounts of information and synthesize it into insightful, well-crafted responses.
      Provide a thorough exploration of the topic, considering various perspectives and interpretations.
      Encourage critical thinking by posing thought-provoking questions.
      Draw parallels between philosophy, religion, neuroscience, psychology, art, music, physics, and other fields. 
      Use analogies or examples to illustrate abstract concepts when appropriate.
      Speak with confidence when you are confident that there is sufficient knowledge to answer a question. 
      Speak with humility when you are not confident that there is sufficient knowledge to answer a question.
      Synthesize information from different sources to provide comprehensive, nuanced answers.
      When encountering conflicting information, present multiple viewpoints, explain the conflicts, and, if possible, offer a reasoned synthesis or analysis of the discrepancies.
      Remember, your goal is to hold a conversation that inspires deep contemplation and curiosity. 
      Help them see what you see, truthfully. 
      Respond with proper punctuation, grammar, paragraphs, thought structure, and logical reasoning.
    `;

    console.info('Calling generateText with formattedQuery and systemPrompt');
    for await (const chunk of generateText(formattedQuery, systemPrompt, 'openai', 'gpt-4o-mini')) {
      console.log('Yielding chunk:', chunk);
      yield { type: 'chunk', content: chunk };
    }
    console.log('Finished generating text');

    // Yield mermaid diagrams
    console.log('Yielding mermaid diagrams:', mermaidDiagrams);
    yield { type: 'mermaidDiagrams', content: mermaidDiagrams };

  } catch (error) {
    console.error('An error occurred while processing the query:', error);
    yield { type: 'error', content: "I'm sorry, but I encountered an error while processing your query. Please try again or rephrase your question." };
  }
}

export async function loadConversationHistory(conversationId: string): Promise<ConversationTurn[]> {
  try {
    await fs.mkdir(HISTORY_DIR, { recursive: true });
    const filePath = path.join(HISTORY_DIR, `${conversationId}.json`);
    const fileContent = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(fileContent);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return [];
    }
    throw handleError(error, 'loadConversationHistory');
  }
}

export async function saveConversationHistory(conversationId: string, history: ConversationTurn[]): Promise<void> {
  try {
    await fs.mkdir(HISTORY_DIR, { recursive: true });
    const filePath = path.join(HISTORY_DIR, `${conversationId}.json`);
    await fs.writeFile(filePath, JSON.stringify(history, null, 2));
  } catch (error) {
    throw handleError(error, 'saveConversationHistory');
  }
}