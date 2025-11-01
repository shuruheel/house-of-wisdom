import { streamText, generateText as aiGenerateText, LanguageModelV1 } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGroq } from 'groq-sdk';
import { config } from '../config';
import { handleError } from '../utils/errorHandler';

// Initialize AI SDK providers
const openai = createOpenAI({
  apiKey: config.openAI.apiKey!,
  compatibility: 'strict',
});

const google = createGoogleGenerativeAI({
  apiKey: config.google.apiKey!,
});

const anthropic = createAnthropic({
  apiKey: config.anthropic.apiKey!,
});

// Note: Groq doesn't have an official AI SDK provider yet,
// but we can use the OpenAI-compatible interface
const groq = createOpenAI({
  apiKey: config.groq.apiKey!,
  baseURL: 'https://api.groq.com/openai/v1',
});

/**
 * Model configurations with latest model IDs
 */
export const models = {
  // OpenAI models
  'gpt-5': openai('gpt-5'),
  'gpt-5-mini': openai('gpt-5-mini'),
  'gpt-5-pro': openai('gpt-5-pro'),
  'gpt-4.1': openai('gpt-4.1'),
  'gpt-4o': openai('gpt-4o'),  // Fallback for compatibility
  'o3-deep-research': openai('o3-deep-research'),
  'o4-mini-deep-research': openai('o4-mini-deep-research'),

  // Google Gemini models
  'gemini-2.5-pro': google('gemini-2.5-pro'),
  'gemini-2.5-flash': google('gemini-2.5-flash'),
  'gemini-1.5-flash': google('gemini-1.5-flash'),  // Fallback for compatibility

  // Anthropic Claude models
  'claude-sonnet-4-5': anthropic('claude-sonnet-4-5-20250929'),
  'claude-opus-4-1': anthropic('claude-opus-4-1-20250805'),
  'claude-haiku-4-5': anthropic('claude-haiku-4-5-20251001'),
  'claude-sonnet-3-5': anthropic('claude-3-5-sonnet-20240620'),  // Fallback for compatibility

  // Groq models (using OpenAI-compatible interface)
  'llama-3.3-70b': groq('llama-3.3-70b-versatile'),
  'llama-3.1-70b': groq('llama-3.1-70b-versatile'),  // Fallback for compatibility
  'llama-3.1-8b': groq('llama-3.1-8b-instant'),
} as const;

export type ModelId = keyof typeof models;

/**
 * Get a model instance by ID
 */
export function getModel(modelId: ModelId): LanguageModelV1 {
  const model = models[modelId];
  if (!model) {
    throw new Error(`Unknown model: ${modelId}`);
  }
  return model;
}

/**
 * Recommended models by use case based on latest-models.md
 */
export const recommendedModels = {
  // Legal reasoning and chain-of-thought
  legalReasoning: 'claude-sonnet-4-5' as ModelId,
  chainOfThought: 'claude-sonnet-4-5' as ModelId,
  mermaidDiagrams: 'claude-sonnet-4-5' as ModelId,

  // Query extraction and entity recognition
  queryExtraction: 'gpt-5-mini' as ModelId,
  entityRecognition: 'gpt-5-mini' as ModelId,

  // Cypher query generation
  cypherGeneration: 'gpt-5' as ModelId,

  // Large document analysis
  largeDocumentAnalysis: 'gemini-2.5-pro' as ModelId,

  // High-volume processing
  highVolumeProcessing: 'gemini-2.5-flash' as ModelId,

  // Complex legal research
  complexResearch: 'claude-opus-4-1' as ModelId,

  // Default response generation
  defaultResponse: 'gemini-2.5-flash' as ModelId,
};

/**
 * Stream text generation using AI SDK
 *
 * @param prompt - User prompt
 * @param systemPrompt - System instruction (optional)
 * @param modelId - Model identifier
 * @param temperature - Sampling temperature (optional)
 * @param maxTokens - Maximum tokens to generate (optional)
 * @returns AsyncGenerator yielding text chunks
 */
export async function* generateText(
  prompt: string,
  systemPrompt?: string,
  modelId: ModelId = recommendedModels.defaultResponse,
  temperature?: number,
  maxTokens?: number
): AsyncGenerator<string, void, unknown> {
  try {
    const model = getModel(modelId);

    const result = streamText({
      model,
      prompt,
      ...(systemPrompt && { system: systemPrompt }),
      ...(temperature !== undefined && { temperature }),
      ...(maxTokens !== undefined && { maxTokens }),
    });

    for await (const textPart of result.textStream) {
      yield textPart;
    }
  } catch (error) {
    throw handleError(error, `generateText (${modelId})`);
  }
}

/**
 * Generate complete text (non-streaming) using AI SDK
 * Useful for structured outputs, tool calling, etc.
 */
export async function generateCompleteText(
  prompt: string,
  systemPrompt?: string,
  modelId: ModelId = recommendedModels.defaultResponse,
  temperature?: number,
  maxTokens?: number
): Promise<string> {
  try {
    const model = getModel(modelId);

    const result = await aiGenerateText({
      model,
      prompt,
      ...(systemPrompt && { system: systemPrompt }),
      ...(temperature !== undefined && { temperature }),
      ...(maxTokens !== undefined && { maxTokens }),
    });

    return result.text;
  } catch (error) {
    throw handleError(error, `generateCompleteText (${modelId})`);
  }
}

/**
 * Legacy compatibility: Generate text with provider/model specification
 * @deprecated Use generateText with ModelId instead
 */
export async function* generateTextLegacy(
  prompt: string,
  systemPrompt: string,
  provider: string,
  model: string,
  temperature?: number,
  maxTokens?: number
): AsyncGenerator<string, void, unknown> {
  // Map old provider/model combinations to new model IDs
  const modelId = mapLegacyModel(provider, model);
  yield* generateText(prompt, systemPrompt, modelId, temperature, maxTokens);
}

/**
 * Map legacy provider/model combinations to new model IDs
 */
function mapLegacyModel(provider: string, model: string): ModelId {
  const mapping: Record<string, ModelId> = {
    'openai:gpt-4o': 'gpt-4o',
    'openai:gpt-4': 'gpt-4o',
    'google:gemini-1.5-flash': 'gemini-1.5-flash',
    'google:gemini-1.5-pro': 'gemini-2.5-pro',
    'anthropic:claude-3-5-sonnet-20240620': 'claude-sonnet-3-5',
    'anthropic:claude-3-sonnet-20240320': 'claude-sonnet-4-5',
    'groq:llama3-70b-8192': 'llama-3.1-70b',
    'groq:llama-3.1-70b-versatile': 'llama-3.1-70b',
  };

  const key = `${provider}:${model}`;
  return mapping[key] || (models[model as ModelId] ? (model as ModelId) : 'gemini-2.5-flash');
}
