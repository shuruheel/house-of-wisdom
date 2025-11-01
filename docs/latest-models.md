# Latest AI Models by Provider

This document outlines the latest available models from OpenAI, Google (Gemini), Anthropic (Claude), and Groq, with recommendations for the House of Wisdom legal/knowledge graph application.

**Last Updated:** October 2025

## Application Use Case

House of Wisdom is a legal knowledge graph application that uses AI models for:
- **Legal reasoning and analysis** - Processing constitutional provisions, articles, amendments
- **Chain-of-thought reasoning** - Generating Mermaid diagrams for complex legal logic
- **Query extraction** - Identifying entities, concepts, and legal questions from user queries
- **Cypher query generation** - Creating Neo4j graph database queries
- **Large context processing** - Handling extensive legal documents and knowledge graphs
- **Structured output generation** - Extracting structured data from legal texts

---

## OpenAI Models

### Recommended Models

#### **GPT-5** (Primary Recommendation)
- **Model ID:** `gpt-5`
- **Context Window:** Not specified in public docs
- **Best For:** Complex legal reasoning, agentic tasks, coding (Cypher generation)
- **Why:** OpenAI's latest flagship model, optimized for coding and agentic tasks - perfect for Cypher query generation and complex legal analysis
- **Status:** Latest frontier model

#### **GPT-5 Pro**
- **Model ID:** `gpt-5-pro`
- **Best For:** When maximum precision is needed for critical legal reasoning
- **Why:** Enhanced version of GPT-5 with smarter and more precise responses

#### **GPT-5 mini**
- **Model ID:** `gpt-5-mini`
- **Best For:** Fast, cost-efficient query extraction and simpler tasks
- **Why:** Faster and more cost-effective for well-defined tasks like entity extraction

#### **GPT-4.1** (Fallback)
- **Model ID:** `gpt-4.1`
- **Best For:** High-quality non-reasoning tasks
- **Why:** Smartest non-reasoning model, good alternative if GPT-5 is unavailable

#### **GPT-4o** (Current Production Model)
- **Model ID:** `gpt-4o`
- **Status:** Currently in use, still available
- **Recommendation:** Upgrade to GPT-5 for better performance

### Deep Research Models (For Complex Legal Analysis)

#### **o3-deep-research**
- **Model ID:** `o3-deep-research`
- **Best For:** Deep legal research requiring extensive reasoning
- **Why:** Most powerful deep research model for complex legal analysis

#### **o4-mini-deep-research**
- **Model ID:** `o4-mini-deep-research`
- **Best For:** Faster, more affordable deep research
- **Why:** More cost-effective alternative to o3-deep-research

### Legacy Models (Deprecated/Not Recommended)
- `gpt-4o-mini` - Still available but superseded by GPT-5 mini
- `gpt-4-turbo` - Older model, use GPT-4.1 instead
- `gpt-3.5-turbo` - Legacy model

**Documentation:** https://platform.openai.com/docs/models

---

## Google Gemini Models

### Recommended Models

#### **Gemini 2.5 Pro** (Primary Recommendation)
- **Model ID:** `gemini-2.5-pro`
- **Context Window:** 1,048,576 tokens (1M tokens)
- **Output Limit:** 65,536 tokens
- **Knowledge Cutoff:** January 2025
- **Capabilities:** 
  - ✅ Thinking (complex reasoning)
  - ✅ Code execution
  - ✅ Function calling
  - ✅ Structured outputs
  - ✅ Long context (1M tokens)
  - ✅ Search grounding
  - ✅ Grounding with Google Maps
- **Best For:** 
  - Complex legal reasoning with large documents
  - Analyzing entire legal codes/constitutions
  - Chain-of-thought reasoning for Mermaid diagrams
- **Why:** Exceptional for large context processing, perfect for analyzing extensive legal documents stored in Neo4j
- **Latest Update:** June 2025

#### **Gemini 2.5 Flash** (Fast & Efficient)
- **Model ID:** `gemini-2.5-flash`
- **Context Window:** 1,048,576 tokens (1M tokens)
- **Output Limit:** 65,536 tokens
- **Knowledge Cutoff:** January 2025
- **Capabilities:** Same as 2.5 Pro but optimized for speed
- **Best For:** 
  - Large-scale processing
  - Low-latency, high-volume tasks
  - Agentic use cases
  - Fast query extraction
- **Why:** Best price-performance ratio, excellent for processing many queries quickly
- **Latest Update:** June 2025

#### **Gemini 2.5 Flash Preview**
- **Model ID:** `gemini-2.5-flash-preview-09-2025`
- **Status:** Preview model (may change with 2-week notice)
- **Best For:** Testing latest features before stable release

### Legacy Models (Still Available)
- `gemini-2.0-flash` - Still available but recommend upgrading to 2.5
- `gemini-1.5-pro` - Old model, superseded by 2.5 Pro

**Documentation:** https://ai.google.dev/gemini-api/docs/models

---

## Anthropic Claude Models

### Recommended Models

#### **Claude Sonnet 4.5** (Primary Recommendation)
- **Model ID:** `claude-sonnet-4-5-20250929`
- **API Alias:** `claude-sonnet-4-5`
- **Context Window:** 200K tokens (1M tokens available in beta)
- **Output Limit:** 64K tokens
- **Knowledge Cutoff:** January 2025 (reliable), July 2025 (training data)
- **Pricing:** $3/input MTok, $15/output MTok
- **Capabilities:**
  - ✅ Extended thinking
  - ✅ Priority tier support
  - ✅ Image input
  - ✅ Multilingual
  - ✅ Vision
- **Best For:**
  - Complex legal reasoning
  - Chain-of-thought reasoning (currently used for Mermaid diagrams)
  - Agentic tasks
  - Coding (Cypher generation)
- **Why:** Best balance of intelligence, speed, and cost. Currently used in `legalReasoningService.ts` and `queryService.ts`
- **Latest Update:** September 2025

#### **Claude Opus 4.1** (For Maximum Quality)
- **Model ID:** `claude-opus-4-1-20250805`
- **API Alias:** `claude-opus-4-1`
- **Context Window:** 200K tokens
- **Output Limit:** 32K tokens
- **Pricing:** $15/input MTok, $75/output MTok
- **Best For:** Specialized reasoning tasks requiring maximum quality
- **Why:** Exceptional model for specialized reasoning, but more expensive

#### **Claude Haiku 4.5** (Fast & Efficient)
- **Model ID:** `claude-haiku-4-5-20251001`
- **API Alias:** `claude-haiku-4-5`
- **Context Window:** 200K tokens
- **Output Limit:** 64K tokens
- **Pricing:** $1/input MTok, $5/output MTok
- **Best For:** Fast query extraction, simple reasoning tasks
- **Why:** Fastest model with near-frontier intelligence, great for cost-sensitive operations

### Legacy Models (Still Available)
- `claude-sonnet-4-20250514` - Older version, migrate to 4.5
- `claude-3-5-sonnet-20240620` - Currently used in code, should upgrade to 4.5

**Documentation:** https://docs.claude.com/en/docs/about-claude/models/overview

---

## Groq Models

### Recommended Models

#### **Llama 3.3 70B Versatile** (Primary Recommendation)
- **Model ID:** `llama-3.3-70b-versatile`
- **Speed:** ~280 tokens/sec
- **Context Window:** 131,072 tokens
- **Output Limit:** 32,768 tokens
- **Pricing:** $0.59/input MTok, $0.79/output MTok
- **Rate Limits:** 300K TPM, 1K RPM (Developer Plan)
- **Best For:** 
  - Fast legal reasoning
  - High-throughput query processing
  - Cost-effective complex reasoning
- **Why:** Latest Llama model with excellent reasoning capabilities and very fast inference speed

#### **OpenAI GPT-OSS 120B** (For Maximum Capability)
- **Model ID:** `openai/gpt-oss-120b`
- **Speed:** ~500 tokens/sec
- **Context Window:** 131,072 tokens
- **Output Limit:** 65,536 tokens
- **Pricing:** $0.15/input MTok, $0.60/output MTok
- **Capabilities:** Built-in browser search and code execution
- **Best For:** Complex reasoning with tool use capabilities
- **Why:** OpenAI's flagship open-weight model with reasoning capabilities

#### **Llama 3.1 8B Instant** (Fast & Lightweight)
- **Model ID:** `llama-3.1-8b-instant`
- **Speed:** ~560 tokens/sec
- **Context Window:** 131,072 tokens
- **Output Limit:** 131,072 tokens
- **Pricing:** $0.05/input MTok, $0.08/output MTok
- **Best For:** Very fast, simple queries
- **Why:** Extremely fast and cost-effective for basic tasks

### Systems (Agentic)

#### **Groq Compound**
- **Model ID:** `groq/compound`
- **Speed:** ~450 tokens/sec
- **Context Window:** 131,072 tokens
- **Output Limit:** 8,192 tokens
- **Capabilities:** Built-in tools (web search, code execution)
- **Best For:** Agentic tasks requiring tool use
- **Why:** AI system that intelligently uses tools to answer queries

### Legacy Models (Not Recommended)
- `llama-3.1-70b-versatile` - Currently used in code, should upgrade to 3.3 70B

**Documentation:** https://console.groq.com/docs/models

---

## Recommended Model Selection by Use Case

### 1. Legal Reasoning & Chain-of-Thought (Mermaid Diagrams)
**Primary:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)  
**Alternative:** Gemini 2.5 Pro (`gemini-2.5-pro`)  
**Fast Alternative:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)

**Rationale:** Current code uses Claude Sonnet 3.5, which should be upgraded to 4.5. Claude excels at structured reasoning and generating Mermaid diagrams.

### 2. Query Extraction & Entity Recognition
**Primary:** GPT-5 mini (`gpt-5-mini`)  
**Alternative:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)  
**Fast Alternative:** Llama 3.1 8B Instant (`llama-3.1-8b-instant`)

**Rationale:** Fast, cost-effective models perfect for structured extraction tasks.

### 3. Cypher Query Generation
**Primary:** GPT-5 (`gpt-5`)  
**Alternative:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)  
**Fallback:** GPT-4.1 (`gpt-4.1`)

**Rationale:** OpenAI models excel at code generation. GPT-5 is specifically optimized for coding tasks.

### 4. Large Document Analysis (Constitutions, Legal Codes)
**Primary:** Gemini 2.5 Pro (`gemini-2.5-pro`)  
**Alternative:** Gemini 2.5 Flash (`gemini-2.5-flash`)  
**Fallback:** Claude Sonnet 4.5 with 1M context beta

**Rationale:** Gemini 2.5 Pro's 1M token context window is unmatched for processing entire legal documents.

### 5. High-Volume Processing
**Primary:** Gemini 2.5 Flash (`gemini-2.5-flash`)  
**Alternative:** Llama 3.3 70B Versatile (`llama-3.3-70b-versatile`)  
**Fastest:** Llama 3.1 8B Instant (`llama-3.1-8b-instant`)

**Rationale:** These models offer the best price-performance for bulk processing.

### 6. Complex Legal Research
**Primary:** o3-deep-research (`o3-deep-research`)  
**Alternative:** Claude Opus 4.1 (`claude-opus-4-1-20250805`)  
**Cost-Effective:** Gemini 2.5 Pro (`gemini-2.5-pro`)

**Rationale:** Deep research models are designed for complex, multi-step reasoning tasks.

---

## Migration Recommendations

### Current Models → Recommended Upgrades

1. **OpenAI:**
   - `gpt-4o` → `gpt-5` (for complex tasks)
   - `gpt-4o` → `gpt-5-mini` (for simple tasks)

2. **Google:**
   - `gemini-1.5-pro-exp-0827` → `gemini-2.5-pro` (for quality)
   - `gemini-1.5-pro-exp-0827` → `gemini-2.5-flash` (for speed)

3. **Anthropic:**
   - `claude-3-5-sonnet-20240620` → `claude-sonnet-4-5-20250929`
   - `claude-3-sonnet-20240320` → `claude-sonnet-4-5-20250929`

4. **Groq:**
   - `llama-3.1-70b-versatile` → `llama-3.3-70b-versatile`

---

## Implementation Notes

### Current Usage in Codebase

Based on code analysis:

1. **`queryService.ts`** (line 101): Uses `gpt-4o` for query extraction
   - **Recommendation:** Upgrade to `gpt-5-mini` for cost efficiency

2. **`legalReasoningService.ts`** (line 183): Uses `claude-3-5-sonnet-20240620` for chain-of-thought
   - **Recommendation:** Upgrade to `claude-sonnet-4-5-20250929`

3. **`queryService.ts`** (line 283): Uses `claude-3-5-sonnet-20240620` for Cypher generation
   - **Recommendation:** Try `gpt-5` for better code generation, or upgrade Claude to 4.5

4. **`aiService.ts`** (line 45): Default `gpt-4o`
   - **Recommendation:** Upgrade to `gpt-5` or `gpt-5-mini`

5. **`aiService.ts`** (line 63): Default `gemini-1.5-flash`
   - **Recommendation:** Upgrade to `gemini-2.5-flash`

6. **`aiService.ts`** (line 81): Default `claude-3-5-sonnet-20240620`
   - **Recommendation:** Upgrade to `claude-sonnet-4-5-20250929`

7. **`aiService.ts`** (line 101): Default `llama3-70b-8192`
   - **Recommendation:** Upgrade to `llama-3.3-70b-versatile`

---

## Cost Considerations

### Estimated Monthly Costs (1M tokens/month)

| Model | Input Cost | Output Cost | Total (50/50 split) |
|-------|------------|-------------|-------------------|
| GPT-5 | ~$10-15 | ~$30-45 | ~$20-30 |
| GPT-5 mini | ~$2-3 | ~$6-9 | ~$4-6 |
| GPT-4.1 | ~$5-7 | ~$15-21 | ~$10-14 |
| Gemini 2.5 Pro | ~$0.50-1.50 | ~$2.50-7.50 | ~$1.50-4.50 |
| Gemini 2.5 Flash | ~$0.10-0.35 | ~$0.50-1.75 | ~$0.30-1.05 |
| Claude Sonnet 4.5 | ~$3 | ~$15 | ~$9 |
| Claude Haiku 4.5 | ~$1 | ~$5 | ~$3 |
| Llama 3.3 70B | ~$0.59 | ~$0.79 | ~$0.69 |
| GPT-OSS 120B | ~$0.15 | ~$0.60 | ~$0.38 |

*Note: Actual costs vary based on usage patterns. Gemini and Groq models offer excellent price-performance.*

---

## Summary

### Best Overall Choices for This Application

1. **Premium Quality:** Claude Sonnet 4.5 + Gemini 2.5 Pro
2. **Balanced:** GPT-5 + Gemini 2.5 Flash
3. **Cost-Optimized:** GPT-5 mini + Llama 3.3 70B + Claude Haiku 4.5

### Key Upgrades Needed

- ✅ Upgrade Claude Sonnet 3.5 → 4.5 (used in reasoning services)
- ✅ Upgrade GPT-4o → GPT-5 (for coding tasks)
- ✅ Upgrade Gemini 1.5 → 2.5 Pro/Flash (for large context)
- ✅ Upgrade Llama 3.1 → 3.3 70B (for Groq usage)

---

## References

- OpenAI Models: https://platform.openai.com/docs/models
- Google Gemini Models: https://ai.google.dev/gemini-api/docs/models
- Anthropic Claude Models: https://docs.claude.com/en/docs/about-claude/models/overview
- Groq Models: https://console.groq.com/docs/models

