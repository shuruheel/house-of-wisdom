# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

House of Wisdom is an AI-powered conversational application that leverages Neo4j graph database for knowledge representation and multiple AI providers (OpenAI, Google, Anthropic, Groq) to generate context-aware responses. The application uses RAG (Retrieval-Augmented Generation) with vector embeddings to fetch relevant knowledge from a knowledge graph.

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
- `OPENAI_API_KEY` - For embeddings (text-embedding-3-large) and GPT-4o
- `GOOGLE_API_KEY` - For Gemini-1.5-flash (default response generation)
- `ANTHROPIC_API_KEY` - For Claude Sonnet (Mermaid diagram generation)
- `GROQ_API_KEY` - For Llama3 support

## Architecture Overview

### Query Processing Pipeline

The application follows a sophisticated multi-stage pipeline for processing user queries:

1. **Query Analysis** (`queryService.ts`):
   - Extracts entities, concepts, time references from user query
   - Identifies if question is legal in nature
   - Generates chain-of-thought sub-questions using GPT-4o
   - Determines ideal mix of knowledge types (events, claims, chunks, concept relationships)

2. **Embedding & Retrieval** (`embeddingService.ts`, `neo4jService.ts`):
   - Computes query embedding using OpenAI's text-embedding-3-large
   - Searches Neo4j graph database for relevant nodes:
     - Events (with temporal relevance scoring)
     - Claims/Ideas
     - Book chunks (from `chunk_embeddings.json`)
     - Concept relationships
     - Legal references (Provisions, Articles, Amendments) if legal question

3. **Context Assembly** (`contextService.ts`):
   - Processes chain-of-thought questions in parallel to generate Mermaid diagrams
   - Assembles comprehensive context from retrieved knowledge
   - Formats context with conversation history

4. **Response Generation** (`conversationService.ts`):
   - Generates streaming response using Google Gemini-1.5-flash by default
   - Returns both text chunks and Mermaid diagrams
   - Saves conversation history to `conversation_histories/{conversationId}.json`

### AI Service Architecture

The `aiService.ts` provides a unified streaming interface for multiple AI providers:
- Each provider has its own generator function (e.g., `generateOpenAIText`, `generateGoogleText`)
- All providers support streaming responses via async generators
- Temperature and max tokens are provider-specific defaults

### Neo4j Graph Structure

**Node Types:**
- Event: name, description, emotion, start_date, embedding
- Claim: content, source, confidence, embedding
- Provision: content, section_number, chapter_number, title_number, embedding
- Article: content, title, embedding
- Amendment: content, title, embedding
- Entity: name, type, embedding
- Concept: name, embedding

**Relationships:**
MENTIONS, CONTAINS, AMENDED_BY, REPLACED_BY, INVOLVES, RELATES_TO, INCLUDES, SUPPORTS, CONTRADICTS, SIMILAR_TO, PART_OF, INFLUENCES, CAUSES, OPPOSES, DEPENDS_ON

**Vector Indexes:**
provision_embedding, entity_embedding, concept_embedding, article_embedding, amendment_embedding

### Frontend Architecture

- Next.js 14 App Router with React Server Components
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
- Sub-questions are generated based on query domain (legal, scientific, historical, etc.)
- Each sub-question processed via `processChainOfThoughtQuestion` with Claude Sonnet
- Mermaid diagrams extracted from responses using regex: `/```mermaid\s*([\s\S]*?)\s*```/g`
- Diagram node labels must avoid: parentheses, curly braces, square brackets, percentage signs

### Legal Question Handling
- When `legal_question === "yes"`, system fetches from legal node types only
- Legal context includes Title/Chapter/Section hierarchy from Provisions
- Uses specialized prompts for legal reasoning and statutory interpretation

### Temporal Relevance
- Events filtered by date range: recent (1 year), latest (3 months), historic (50+ years)
- Time relevance scoring uses exponential decay functions
- Coefficients vary by query type (recent, historic, default)

### Rate Limiting
- Query element extraction is rate-limited to 5 requests/minute via `limiter`

### Caching
- Embedding cache (NodeCache) with 1-hour TTL
- Chunk embeddings loaded once from `chunk_embeddings.json`

## Common Patterns

### Adding a New AI Provider
1. Add API key to `config.ts`
2. Initialize client in `aiService.ts`
3. Implement async generator function (e.g., `generateNewProviderText`)
4. Add case to switch statement in `generateText`

### Modifying Context Retrieval
- Adjust `ideal_mix` defaults in `queryService.ts` (events, claims, chunks, concept_relationships)
- Modify similarity thresholds in service functions (default 0.3)
- Update `getRelevantEventsAndClaims` or `getRelevantConceptRelationships` in `neo4jService.ts`

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
- `LegalInfoContext`: provisions, articles, amendments, relationships, comparisons

## UI Components

- Shadcn UI components in `app/components/ui/`
- Custom `MermaidDiagramRenderer` for rendering Mermaid diagrams client-side
- ReactMarkdown with rehype-raw and rehype-sanitize for AI responses
- Keyboard shortcuts via react-hotkeys-hook
- Toggle diagram visibility with Eye/EyeOff icons per message

## Notes

- The default AI provider for responses is Google Gemini-1.5-flash
- Mermaid diagram generation uses Anthropic Claude Sonnet
- Query analysis uses OpenAI GPT-4o
- All embeddings use OpenAI text-embedding-3-large
- Neo4j connection uses encryption with custom certificate at `app/lib/public.crt`
