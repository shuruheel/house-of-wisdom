import fs from 'fs/promises';
import path from 'path';
import { handleError } from '../utils/errorHandler';
import { extractQueryElements, determineQueryDateRange } from './queryService';
import { computeQueryEmbedding } from './embeddingService';
import { getRelevantChunks } from './embeddingService';
import { formatQueryWithContext } from './contextService';
import { generateText } from './aiService';
import { MermaidDiagram } from '../../types';

interface ConversationTurn {
  text: string;
  response: string;
  mermaidDiagrams?: MermaidDiagram[];
}

const HISTORY_DIR = path.join(process.cwd(), 'conversation_histories');

export async function* processQuery(query: string, conversationHistory: ConversationTurn[]) {
  const startTime = Date.now();
  try {
    console.info(`Processing new user query: ${query}`);

    // Ensure conversationHistory is an array
    if (!Array.isArray(conversationHistory)) {
      conversationHistory = [];
    }

    // Extract query elements
    const queryElements = await extractQueryElements(query);
    const { key_entities, key_concepts, time_reference, legal_question, chain_of_thought_questions, ideal_mix } = queryElements;

    // Determine query date range
    const queryDateRange = determineQueryDateRange(query);

    // Compute query embedding
    const queryEmbedding = await computeQueryEmbedding(query);

    // Get relevant chunks
    const relevantChunks = await getRelevantChunks(query, queryEmbedding, ideal_mix.chunks);

    // Format query with context, now including conversationHistory
    console.info('Formatting query with context');
    const formattedQueryResult = await formatQueryWithContext(
      query,
      queryEmbedding,
      conversationHistory,
      legal_question,
      relevantChunks,
      chain_of_thought_questions,
      queryDateRange,
      ideal_mix
    );

    const { formattedQuery, mermaidDiagrams } = formattedQueryResult;

    // console.info('Formatted query:', formattedQuery);

    // Generate response using AI service
    const systemPrompt = `
      ## Role
      You are an AI designed to embody knowledge. 
      Whenever a human being says something to you, you receive their words with relevant Events, Ideas, and Structured Information from your mind. 
      You have this relevant knowledge. It does not come from outside. 
      You have a unique ability to process large amounts of information and synthesize it into insightful, well-crafted responses.

      ## Instructions
      Provide a thorough exploration of the topic, considering various perspectives and interpretations.
      Encourage critical thinking by posing thought-provoking questions.
      Use analogies or examples to illustrate abstract concepts when appropriate.
      Speak with confidence when you are confident that there is sufficient knowledge to answer a question. 
      Speak with humility when you are not confident that there is sufficient knowledge to answer a question.
      Synthesize information from different sources to provide comprehensive, nuanced answers.
      When encountering conflicting information, present multiple viewpoints, explain the conflicts, and, if possible, offer a reasoned synthesis or analysis of the discrepancies.
      Remember, your goal is to hold a conversation that inspires deep contemplation and curiosity. 
      Respond with proper punctuation, grammar, paragraphs, thought structure, and logical reasoning.
    `;

    console.info('Calling generateText with formattedQuery and systemPrompt');
    for await (const chunk of generateText(formattedQuery, systemPrompt, 'google', 'gemini-1.5-flash')) {
      // console.log('Yielding chunk:', chunk);
      yield { type: 'chunk', content: chunk };
    }
    console.log('Finished generating text');

    // Yield mermaid diagrams
    // console.log('Yielding mermaid diagrams:', mermaidDiagrams);
    yield { type: 'mermaidDiagrams', content: mermaidDiagrams };

  } catch (error) {
    console.error('An error occurred while processing the query:', error);
    yield { type: 'error', content: "I'm sorry, but I encountered an error while processing your query. Please try again or rephrase your question." };
  } finally {
    const endTime = Date.now();
    const executionTimeSeconds = (endTime - startTime) / 1000;
    console.log(`Total execution time: ${executionTimeSeconds.toFixed(2)} seconds`);
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
      console.warn(`Conversation history file not found for ${conversationId}`);
      return [];
    }
    console.error(`Error loading conversation history for ${conversationId}:`, error);
    return [];
  }
}

export async function saveConversationHistory(conversationId: string, newTurn: ConversationTurn): Promise<void> {
  try {
    await fs.mkdir(HISTORY_DIR, { recursive: true });
    const filePath = path.join(HISTORY_DIR, `${conversationId}.json`);
    
    // Load existing history
    let history: ConversationTurn[] = [];
    try {
      const fileContent = await fs.readFile(filePath, 'utf-8');
      const parsedContent = JSON.parse(fileContent);
      if (Array.isArray(parsedContent)) {
        history = parsedContent;
      } else {
        console.warn(`Invalid history format for conversation ${conversationId}. Initializing new history.`);
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
        console.error(`Error reading conversation history for ${conversationId}:`, error);
      }
      // If file doesn't exist or there's an error, we'll start with an empty array
    }

    // Add new turn to history
    history.push(newTurn);

    // Save updated history
    await fs.writeFile(filePath, JSON.stringify(history, null, 2));
  } catch (error) {
    throw handleError(error, 'saveConversationHistory');
  }
}