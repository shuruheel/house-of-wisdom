import OpenAI from 'openai';
import { GoogleGenerativeAI } from '@google/generative-ai';
import Anthropic from '@anthropic-ai/sdk';
import Groq from 'groq-sdk';
import { config } from '../config';
import { handleError } from '../utils/errorHandler';

// Initialize API clients
const openai = new OpenAI({ apiKey: config.openAI.apiKey! });
const googleAI = new GoogleGenerativeAI(config.google.apiKey!);
const anthropic = new Anthropic({ apiKey: config.anthropic.apiKey! });
const groq = new Groq({ apiKey: config.groq.apiKey! });

export async function* generateText(
  prompt: string,
  systemPrompt: string,
  provider: string,
  model: string,
  temperature?: number,
  maxTokens?: number
): AsyncGenerator<string, void, unknown> {
  try {
    switch (provider) {
      case 'openai':
        yield* generateOpenAIText(prompt, systemPrompt, model, temperature, maxTokens);
        break;
      case 'google':
        yield* generateGoogleText(prompt, systemPrompt, model, temperature, maxTokens);
        break;
      case 'anthropic':
        yield* generateAnthropicText(prompt, systemPrompt, model, temperature, maxTokens);
        break;
      case 'groq':
        yield* generateGroqText(prompt, systemPrompt, model, temperature, maxTokens);
        break;
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }
  } catch (error) {
    throw handleError(error, `generateText (${provider} ${model})`);
  }
}

// Implement the specific generator functions for each provider
async function* generateOpenAIText(prompt: string, systemPrompt?: string, model = 'gpt-4o', temperature = 0.2, maxTokens = 3000) {
  const messages: OpenAI.ChatCompletionMessageParam[] = systemPrompt
    ? [{ role: 'system', content: systemPrompt }, { role: 'user', content: prompt }]
    : [{ role: 'user', content: prompt }];

  const stream = await openai.chat.completions.create({
    model,
    messages,
    temperature,
    max_tokens: maxTokens,
    stream: true,
  });

  for await (const chunk of stream) {
    yield chunk.choices[0]?.delta?.content || '';
  }
}

async function* generateGoogleText(prompt: string, systemPrompt?: string, model = 'gemini-1.5-flash', temperature = 0.1, maxTokens = 3000) {
  const genModel = googleAI.getGenerativeModel({
    model,
    generationConfig: {
      temperature,
      maxOutputTokens: maxTokens,
    },
    // Add system instruction if provided
    ...(systemPrompt && { systemInstruction: systemPrompt }),
  });

  const result = await genModel.generateContentStream(prompt);

  for await (const chunk of result.stream) {
    yield chunk.text();
  }
}

async function* generateAnthropicText(prompt: string, systemPrompt?: string, model = 'claude-3-5-sonnet-20240620', temperature = 0.2, maxTokens = 3000) {
  const messages: Anthropic.MessageParam[] = [
    { role: 'user', content: prompt }
  ];

  const stream = await anthropic.messages.stream({
    messages,
    model,
    max_tokens: maxTokens,
    temperature,
    system: systemPrompt,
  });

  for await (const event of stream) {
    if (event.type === 'content_block_delta' && 'text' in event.delta) {
      yield event.delta.text;
    }
  }
}

async function* generateGroqText(prompt: string, systemPrompt?: string, model = 'llama3-70b-8192', temperature = 1.2, maxTokens = 3000) {
  const messages: { role: 'system' | 'user', content: string }[] = systemPrompt
    ? [{ role: 'system', content: systemPrompt }, { role: 'user', content: prompt }]
    : [{ role: 'user', content: prompt }];

  const stream = await groq.chat.completions.create({
    messages,
    model,
    temperature,
    max_tokens: maxTokens,
    stream: true,
  });

  for await (const chunk of stream) {
    yield chunk.choices[0]?.delta?.content || '';
  }
}