# AI SDK by Vercel - Introduction

**URL:** https://v6.ai-sdk.dev/docs/introduction

The AI SDK is the TypeScript toolkit designed to help developers build AI-powered applications and agents with React, Next.js, Vue, Svelte, Node.js, and more.

## Why use the AI SDK?

Integrating large language models (LLMs) into applications is complicated and heavily dependent on the specific model provider you use.

The AI SDK standardizes integrating artificial intelligence (AI) models across supported providers. This enables developers to focus on building great AI applications, not waste time on technical details.

### Example: Generate text with various models

```typescript
import { generateText } from "ai"
import { xai } from "@ai-sdk/xai"

const { text } = await generateText({
  model: xai("grok-4"),
  prompt: "What is love?"
})
```

Output:
> Love is a universal emotion that is characterized by feelings of affection, attachment, and warmth towards someone or something. It is a complex and multifaceted experience that can take many different forms, including romantic love, familial love, platonic love, and self-love.

## Main Libraries

The AI SDK has two main libraries:

1. **AI SDK Core**: A unified API for generating text, structured objects, tool calls, and building agents with LLMs.
2. **AI SDK UI**: A set of framework-agnostic hooks for quickly building chat and generative user interface.

## Model Providers

The AI SDK supports multiple model providers including:

- **xAI Grok** - Image Input, Image Generation, Object Generation, Tool Usage, Tool Streaming
- **OpenAI** - Image Input, Image Generation, Object Generation, Tool Usage, Tool Streaming
- **Azure** - Image Input, Object Generation, Tool Usage, Tool Streaming
- **Anthropic** - Image Input, Object Generation, Tool Usage, Tool Streaming
- **Amazon Bedrock** - Image Input, Image Generation, Object Generation, Tool Usage, Tool Streaming
- **Groq** - Object Generation, Tool Usage, Tool Streaming
- **Fal AI** - Image Generation
- **DeepInfra** - Image Input, Object Generation, Tool Usage, Tool Streaming
- **Google Generative AI** - Image Input, Object Generation, Tool Usage, Tool Streaming
- **Google Vertex AI** - Image Input, Image Generation, Object Generation, Tool Usage, Tool Streaming
- **Mistral** - Image Input, Object Generation, Tool Usage, Tool Streaming
- **Together.ai** - Object Generation, Tool Usage, Tool Streaming
- **Cohere** - Tool Usage, Tool Streaming
- **Fireworks** - Image Generation, Object Generation, Tool Usage, Tool Streaming
- **DeepSeek** - Object Generation, Tool Usage, Tool Streaming
- **Cerebras** - Object Generation, Tool Usage, Tool Streaming
- **Perplexity**
- **Luma AI** - Image Generation
- **Baseten** - Object Generation, Tool Usage

## Templates

The AI SDK provides various templates for different use cases:

### Starter Kits
- **Chatbot Starter Template** - Uses AI SDK and Next.js with persistence, multi-modal chat
- **Internal Knowledge Base (RAG)** - Uses AI SDK Language Model Middleware for RAG
- **Multi-Modal Chat** - Uses Next.js and AI SDK useChat hook
- **Semantic Image Search** - Built with Next.js, AI SDK, and Postgres
- **Natural Language PostgreSQL** - Query PostgreSQL using natural language with AI SDK and GPT-4o

### Feature Exploration
- **Feature Flags Example** - AI SDK with Next.js for dynamic model switching
- **Chatbot with Telemetry** - AI SDK chatbot with OpenTelemetry support
- **Structured Object Streaming** - Uses AI SDK useObject hook
- **Multi-Step Tools** - Uses AI SDK streamText function to handle multiple tool steps automatically

### Frameworks
- Next.js OpenAI Starter
- Nuxt OpenAI Starter
- SvelteKit OpenAI Starter
- Solid OpenAI Starter

### Generative UI
- Gemini Chatbot
- Generative UI with RSC (experimental)

### Security
- Bot Protection (with Kasada)
- Rate Limiting (with Vercel KV)

## Community

Join the AI SDK community on GitHub Discussions for questions and support.

## llms.txt Documentation

The entire AI SDK documentation is available in Markdown format at `ai-sdk.dev/llms.txt`. This can be used to ask any LLM questions about the AI SDK based on the most up-to-date documentation.

