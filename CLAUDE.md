# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

House of Wisdom is an AI-powered conversational application that leverages Neo4j graph database for knowledge representation and multiple AI providers (OpenAI, Google, Anthropic, Groq) via Vercel AI SDK 6 to generate context-aware responses. The application uses RAG (Retrieval-Augmented Generation) with vector embeddings to fetch relevant knowledge from a knowledge graph.

**Latest Update:** Refactored to use Next.js 16, React 19, and Vercel AI SDK 6 with the latest AI models.

## Development Commands

### Local Development
```bash
npm install                 # Install dependencies
npm run dev                 # Start Next.js dev server at http://localhost:3000
npm run build              # Build production bundle
npm run start              # Start production server
npm run lint               # Run ESLint
```

### Environment Variables Required
Create a `.env.local` file with:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` - Neo4j connection
- `OPENAI_API_KEY` - For embeddings (text-embedding-3-large) and GPT-5/GPT-5 mini
- `GOOGLE_API_KEY` - For Gemini 2.5 Pro/Flash (default response generation)
- `ANTHROPIC_API_KEY` - For Claude Sonnet 4.5 (Mermaid diagram generation)
- `GROQ_API_KEY` - For Llama 3.3 70B support

## Architecture Overview

### Tech Stack

- **Frontend:** Next.js 16 with React 19, App Router, Server Components
- **AI SDK:** Vercel AI SDK 6 (unified interface for all AI providers)
- **Database:** Neo4j graph database with vector search
- **AI Models:**
  - Query extraction: GPT-5 mini
  - Cypher generation: GPT-5
  - Legal reasoning & Mermaid diagrams: Claude Sonnet 4.5
  - Response generation: Gemini 2.5 Flash (default)
  - Large document analysis: Gemini 2.5 Pro

### Query Processing Pipeline

The application follows a sophisticated multi-stage pipeline for processing user queries:

1. **Query Analysis** (`queryService.ts`):
   - Extracts entities, concepts, time references using AI SDK's `generateObject` with Zod schemas
   - Identifies if question is legal in nature
   - Generates chain-of-thought sub-questions using GPT-5 mini
   - Determines ideal mix of knowledge types (events, claims, concept relationships)

2. **Embedding & Retrieval** (`embeddingService.ts`, `neo4jService.ts`):
   - Computes query embedding using OpenAI's text-embedding-3-large
   - Searches Neo4j graph database for relevant nodes using vector indexes:
     - Events (with temporal relevance scoring)
     - Claims/Ideas
     - Concept relationships
     - Legal references (Provisions, Articles, Amendments, Scopes) if legal question

3. **Context Assembly** (`contextService.ts`):
   - Processes chain-of-thought questions in parallel to generate Mermaid diagrams
   - Assembles comprehensive context from retrieved knowledge
   - Formats context with conversation history

4. **Response Generation** (`conversationService.ts`):
   - Generates streaming response using Gemini 2.5 Flash by default
   - Returns both text chunks and Mermaid diagrams
   - Saves conversation history to `conversation_histories/{conversationId}.json`

### AI Service Architecture (Vercel AI SDK 6)

The `aiService.ts` provides a unified interface using Vercel AI SDK 6:

- **Provider Initialization:** Uses `createOpenAI`, `createGoogleGenerativeAI`, `createAnthropic`
- **Model Registry:** Centralized model definitions with latest versions
- **Recommended Models:** Use-case specific model recommendations
- **Unified API:** `generateText` for streaming, `generateCompleteText` for non-streaming
- **Structured Outputs:** Support for Zod schemas via `generateObject`

**Example:**
```typescript
import { generateText, recommendedModels } from './aiService';

for await (const chunk of generateText(
  prompt,
  systemPrompt,
  recommendedModels.mermaidDiagrams  // Uses Claude Sonnet 4.5
)) {
  // Process chunk
}
```

### Neo4j Graph Structure

**Node Types (Updated):**
- **Event:** name, description, emotion, start_date, end_date, embedding
- **Claim:** content, source, confidence, embedding
- **Provision:** content, section_number, section_title, chapter_number, title_number, embedding
- **Scope:** content, section_number, section_title, chapter_number, title_number, label, embedding
- **Article:** content, title, number, embedding
- **Amendment:** content, title, number, embedding
- **Entity:** name, type, subType, description, biography, embedding
- **Concept:** name, description, definition, domain, embedding
- **And 20+ more:** Thought, Proposition, Law, ScientificInsight, ReasoningChain, ReasoningStep, DataPoint, Attribute, Emotion, Location, Poetry, Report, Book, Chapter, Title, LegalCode, Constitution, BillOfRights, Condition, Consequence, Definition

**Relationships (Expanded):**
MENTIONS, CONTAINS, AMENDED_BY, REPLACED_BY, INVOLVES, RELATES_TO, INCLUDES, SUPPORTS, CONTRADICTS, SIMILAR_TO, PART_OF, INFLUENCES, CAUSES, OPPOSES, DEPENDS_ON, KNOWS, FRIEND_OF, MEMBER_OF, IS_A, HAS_PART, LOCATED_IN, HAS_TIME, PARTICIPANT, AGENT, EXPRESSES_EMOTION, BELIEVES, DERIVES_FROM, and many more.

**Vector Indexes (Updated):**
- `event_embedding_index`
- `claim_embedding_index`
- `provision_embedding_index`
- `scope_embedding_index` (NEW)
- `article_embedding_index`
- `amendment_embedding_index`
- `entity_embedding_index`
- `concept_embedding_index`

Note: `chunk_embedding` index has been removed in favor of scope embeddings.

### Frontend Architecture

- **Next.js 16** with Turbopack (default bundler)
- **React 19** with Server Components and async/await patterns
- Main chat interface in `app/page.tsx` with streaming message handling
- Conversation state managed client-side with local React state
- Conversations persisted via API routes to filesystem
- Mermaid diagrams rendered client-side via `MermaidDiagramRenderer.tsx`
- Keyboard navigation: Up/Down arrows to switch conversations

### API Routes

**POST /api/conversation**
- Accepts either: `{query, conversationId}` for chat or `{id, name, messages}` for save
- Returns Server-Sent Events stream for chat responses
- Streams chunks as `data: {chunk: "..."}\n\n`
- Streams diagrams as `data: {mermaidDiagrams: [...]}\n\n`

**GET /api/conversations**
- Returns list of saved conversations from `conversation_histories/`

**DELETE /api/conversation?id={conversationId}**
- Deletes conversation file from filesystem

## Key Implementation Details

### Chain-of-Thought Reasoning

- Sub-questions generated using GPT-5 mini with structured Zod schemas
- Each sub-question processed via `processChainOfThoughtQuestion` with Claude Sonnet 4.5
- Mermaid diagrams extracted from responses using regex: `/```mermaid\s*([\s\S]*?)\s*```/g`
- Diagram node labels must avoid: parentheses, curly braces, square brackets, percentage signs

### Legal Question Handling

- When `legal_question === "yes"`, system fetches from legal node types only
- Queries `provision_embedding_index`, `article_embedding_index`, `amendment_embedding_index`, `scope_embedding_index`
- Legal context includes Title/Chapter/Section hierarchy from Provisions and Scopes
- Uses specialized prompts for legal reasoning and statutory interpretation
- Claude Sonnet 4.5 used for superior legal analysis

### Temporal Relevance

- Events filtered by date range: recent (1 year), latest (3 months), historic (50+ years)
- Time relevance scoring uses exponential decay functions
- Coefficients vary by query type (recent, historic, default)

### AI SDK 6 Features Used

- **Structured Outputs:** `generateObject` with Zod schemas for type-safe extraction
- **Streaming:** `streamText` for real-time response generation
- **Model Registry:** Centralized model configuration with use-case recommendations
- **Provider Abstraction:** Unified interface across OpenAI, Google, Anthropic, Groq

### Rate Limiting

- Query element extraction is rate-limited to 5 requests/minute via `limiter`

### Caching

- Embedding cache (NodeCache) with 1-hour TTL
- No chunk embeddings (removed in favor of scope embeddings)

## Common Patterns

### Using the Latest AI Models

```typescript
import { generateText, recommendedModels } from './aiService';

// For query extraction (GPT-5 mini)
const result = await generateObject({
  model: getModel(recommendedModels.queryExtraction),
  schema: queryElementsSchema,
  prompt,
});

// For Mermaid diagrams (Claude Sonnet 4.5)
for await (const chunk of generateText(
  prompt,
  systemPrompt,
  recommendedModels.mermaidDiagrams
)) {
  response += chunk;
}

// For Cypher generation (GPT-5)
const result = await aiGenerateText({
  model: getModel(recommendedModels.cypherGeneration),
  prompt,
});
```

### Structured Output with Zod

```typescript
import { generateObject } from 'ai';
import { z } from 'zod';

const schema = z.object({
  entities: z.array(z.string()),
  concepts: z.array(z.string()),
});

const result = await generateObject({
  model: getModel('gpt-5-mini'),
  schema,
  prompt,
});
```

### Vector Search Queries

```typescript
// Event and Claim search
CALL db.index.vector.queryNodes('event_embedding_index', $max_items, $query_embedding)
YIELD node AS n, score AS similarity
WHERE similarity >= $similarity_threshold

// Legal reference search
CALL db.index.vector.queryNodes('provision_embedding_index', $max_items, $query_embedding)
YIELD node AS n, score AS similarity
WHERE similarity >= $similarity_threshold
  AND NOT n.section_title IN ['Transferred', 'Repealed', 'Omitted']
```

### Conversation Storage

- Conversations stored as JSON files: `conversation_histories/{id}.json`
- Format: Array of `ConversationTurn` objects with `text`, `response`, `mermaidDiagrams`
- Use `loadConversationHistory` and `saveConversationHistory` helpers

## TypeScript Types

Key interfaces defined in `app/types/index.ts`:
- `Message`: UI message with id, text, sender, optional mermaidDiagrams
- `Conversation`: id, name, messages array
- `ConversationTurn`: text, response, optional mermaidDiagrams (for storage)
- `ChainOfThoughtQuestion`: question, reasoning_types array
- `MermaidDiagram`: question, diagram string
- `LegalInfoContext`: provisions, articles, amendments, scopes, relationships, comparisons

## UI Components

- Shadcn UI components in `app/components/ui/`
- Custom `MermaidDiagramRenderer` for rendering Mermaid diagrams client-side
- ReactMarkdown with rehype-raw and rehype-sanitize for AI responses
- Keyboard shortcuts via react-hotkeys-hook
- Toggle diagram visibility with Eye/EyeOff icons per message

## Latest Model IDs

**OpenAI:**
- `gpt-5` - Latest flagship model
- `gpt-5-mini` - Fast, cost-efficient
- `gpt-5-pro` - Maximum precision
- `gpt-4.1` - High-quality non-reasoning
- `o3-deep-research` - Deep research model

**Google Gemini:**
- `gemini-2.5-pro` - 1M token context, thinking capability
- `gemini-2.5-flash` - Fast, efficient, 1M context

**Anthropic Claude:**
- `claude-sonnet-4-5` - Latest Sonnet (Sept 2025)
- `claude-opus-4-1` - Maximum quality
- `claude-haiku-4-5` - Fast, near-frontier

**Groq:**
- `llama-3.3-70b-versatile` - Latest Llama model
- `openai/gpt-oss-120b` - OpenAI's open-weight model

## Migration Notes

This codebase was recently refactored from:
- Next.js 14 → Next.js 16
- React 18 → React 19
- Custom AI service → Vercel AI SDK 6
- Old model IDs → Latest models (GPT-5, Gemini 2.5, Claude 4.5, Llama 3.3)
- Chunk embeddings → Scope embeddings
- Manual JSON parsing → Zod schemas with `generateObject`

Key changes:
- All AI provider calls now go through Vercel AI SDK 6
- Structured outputs use `generateObject` with Zod validation
- Vector indexes updated to use new names (e.g., `event_embedding_index` instead of manual cosine similarity)
- Model IDs centralized in `aiService.ts` with use-case recommendations
- Turbopack is now the default bundler

## Notes

- The default AI provider for responses is Google Gemini 2.5 Flash
- Mermaid diagram generation uses Anthropic Claude Sonnet 4.5
- Query analysis uses OpenAI GPT-5 mini
- All embeddings use OpenAI text-embedding-3-large
- Neo4j connection uses encryption with custom certificate at `app/lib/public.crt`
- Vercel AI SDK 6 provides unified interface across all providers
