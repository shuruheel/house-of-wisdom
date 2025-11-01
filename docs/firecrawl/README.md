# Firecrawl Documentation

This directory contains documentation for the [Firecrawl](https://firecrawl.dev) API - a powerful web scraping and data extraction service that turns websites into LLM-ready data.

## Overview

Firecrawl is an API service that takes a URL, crawls it, and converts it into clean markdown. It handles all the hard stuff like proxies, anti-bot mechanisms, and dynamic content rendering.

## Documentation Files

### [introduction.md](./introduction.md)
**Quickstart Guide** - Get started with Firecrawl basics
- Installation and setup
- Basic scraping examples
- Crawling multiple pages
- JSON mode and structured data extraction
- Actions for interacting with pages
- Search functionality
- TypeScript/Node.js code examples

### [advanced-scraping-guide.md](./advanced-scraping-guide.md)
**Advanced Scraping Options** - Deep dive into all scraping features
- Scrape endpoint options (formats, tags, timeouts, etc.)
- Actions for browser automation
- PDF parsing
- Extract endpoint for async extraction
- Crawling options and configuration
- Map endpoint for link discovery
- TypeScript/Node.js code examples

### [search.md](./search.md)
**Search API** - Web search with content scraping
- Basic search usage
- Search result types (web, news, images)
- Category-based search (GitHub, research, PDFs)
- HD image search
- Time-based filtering
- Location customization
- Cost implications and optimization
- TypeScript/Node.js code examples

### [llms.txt](./llms.txt)
**Resource Links** - Comprehensive list of Firecrawl resources
- Core features and tools
- Blog posts and tutorials
- AI/LLM integration guides
- Technical deep dives
- Company updates and use cases

## Key Features

### 🔥 Core Capabilities
- **Scrape**: Single URL scraping with LLM-ready output
- **Crawl**: Full website crawling with automatic discovery
- **Map**: Fast URL discovery and sitemap generation
- **Search**: Web search with optional content scraping
- **Extract**: AI-powered structured data extraction

### 🎯 Output Formats
- Markdown
- HTML (raw and cleaned)
- JSON (with schema or prompt-based)
- Screenshots
- Links and metadata
- Images

### 🛠️ Advanced Features
- Browser actions (click, scroll, type, wait)
- PDF parsing
- Custom headers for auth
- Proxy support
- Dynamic content rendering (JavaScript)
- Time-based and location-based search
- Category filtering (GitHub, research, PDFs)

## Integration with Agent Dashboard

### Potential Use Cases

1. **Research Tool** - Agents can use Firecrawl to:
   - Search the web for information
   - Extract structured data from websites
   - Crawl documentation sites
   - Parse PDFs and documents

2. **Data Collection** - Automate:
   - Competitive analysis
   - Market research
   - News monitoring
   - Content aggregation

3. **Memory Enhancement** - Feed Supermemory with:
   - Crawled website content
   - Extracted structured data
   - Search results
   - Document summaries

### Implementation Notes

When integrating Firecrawl into the Agent Dashboard:

- Store API key in `tool_configs` table (encrypted)
- Create Firecrawl tools for the AI SDK:
  - `firecrawlScrape` - Scrape a single URL
  - `firecrawlCrawl` - Crawl an entire website
  - `firecrawlSearch` - Search the web
  - `firecrawlExtract` - Extract structured data
- Log activities to `activities` table with type `webpage_viewed` or `research`
- Handle rate limits and errors gracefully
- Use async/await for long-running crawl operations

### Example Tool Implementation

```typescript
import Firecrawl from '@mendable/firecrawl-js';
import { tool } from 'ai';
import { z } from 'zod';

export const firecrawlScrape = tool({
  description: 'Scrape a website and convert it to clean markdown',
  parameters: z.object({
    url: z.string().url().describe('The URL to scrape'),
    formats: z.array(z.string()).optional().describe('Output formats: markdown, html, links'),
    onlyMainContent: z.boolean().optional().describe('Extract only main content (default: true)')
  }),
  execute: async ({ url, formats = ['markdown'], onlyMainContent = true }) => {
    const firecrawl = new Firecrawl({ apiKey: process.env.FIRECRAWL_API_KEY });
    
    const result = await firecrawl.scrape(url, {
      formats,
      onlyMainContent
    });
    
    return {
      markdown: result.markdown,
      metadata: result.metadata
    };
  }
});
```

## API Authentication

All Firecrawl API requests require an API key:

```typescript
import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR-API-KEY' });
```

Get your API key by signing up at [firecrawl.dev](https://www.firecrawl.dev/).

## Resources

- **Official Docs**: https://docs.firecrawl.dev
- **API Reference**: https://docs.firecrawl.dev/api-reference
- **GitHub**: https://github.com/mendableai/firecrawl
- **NPM Package**: [@mendable/firecrawl-js](https://www.npmjs.com/package/@mendable/firecrawl-js)
- **Pricing**: https://www.firecrawl.dev/pricing
- **Blog**: https://www.firecrawl.dev/blog

## License

Firecrawl is open source (AGPL-3.0 license) with a hosted cloud offering.

---

**Last Updated**: October 2024  
**Documentation Source**: Official Firecrawl Documentation  
**Code Examples**: TypeScript/Node.js

