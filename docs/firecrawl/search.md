# Search

Search the web and get full content from results.

Firecrawl's search API allows you to perform web searches and optionally scrape the search results in one operation.

- Choose specific output formats (markdown, HTML, links, screenshots)
- Search the web with customizable parameters (location, etc.)
- Optionally retrieve content from search results in various formats
- Control the number of results and set timeouts

For details, see the Search Endpoint API Reference.

## Performing a Search with Firecrawl

### /search endpoint

Used to perform web searches and optionally retrieve content from the results.

### Installation

```typescript
// npm install @mendable/firecrawl-js

import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR-API-KEY' });
```

### Basic Usage

```typescript
import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR-API-KEY' });

const results = await firecrawl.search({
  query: 'firecrawl',
  limit: 3
});
console.log(results);
```

### Response

SDKs will return the data object directly. cURL will return the complete payload.

```json
{
  "success": true,
  "data": {
    "web": [
      {
        "url": "https://www.firecrawl.dev/",
        "title": "Firecrawl - The Web Data API for AI",
        "description": "The web crawling, scraping, and search API for AI. Built for scale. Firecrawl delivers the entire internet to AI agents and builders.",
        "position": 1
      },
      {
        "url": "https://github.com/mendableai/firecrawl",
        "title": "mendableai/firecrawl: Turn entire websites into LLM-ready ... - GitHub",
        "description": "Firecrawl is an API service that takes a URL, crawls it, and converts it into clean markdown or structured data.",
        "position": 2
      }
    ],
    "images": [
      {
        "title": "Quickstart | Firecrawl",
        "imageUrl": "https://mintlify.s3.us-west-1.amazonaws.com/firecrawl/logo/logo.png",
        "imageWidth": 5814,
        "imageHeight": 1200,
        "url": "https://docs.firecrawl.dev/",
        "position": 1
      }
    ],
    "news": [
      {
        "title": "Y Combinator startup Firecrawl is ready to pay $1M to hire three AI agents as employees",
        "url": "https://techcrunch.com/2025/05/17/y-combinator-startup-firecrawl-is-ready-to-pay-1m-to-hire-three-ai-agents-as-employees/",
        "snippet": "It's now placed three new ads on YC's job board for "AI agents only" and has set aside a $1 million budget total to make it happen.",
        "date": "3 months ago",
        "position": 1
      }
    ]
  }
}
```

## Search result types

In addition to regular web results, Search supports specialized result types via the `sources` parameter:

- **web**: standard web results (default)
- **news**: news-focused results
- **images**: image search results

## Search Categories

Filter search results by specific categories using the `categories` parameter:

- **github**: Search within GitHub repositories, code, issues, and documentation
- **research**: Search academic and research websites (arXiv, Nature, IEEE, PubMed, etc.)
- **pdf**: Search for PDFs

### GitHub Category Search

Search specifically within GitHub repositories:

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "web scraping python",
    "categories": ["github"],
    "limit": 10
  }'
```

### Research Category Search

Search academic and research websites:

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "machine learning transformers",
    "categories": ["research"],
    "limit": 10
  }'
```

### Mixed Category Search

Combine multiple categories in one search:

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "neural networks",
    "categories": ["github", "research"],
    "limit": 15
  }'
```

### Category Response Format

Each search result includes a `category` field indicating its source:

```json
{
  "success": true,
  "data": {
    "web": [
      {
        "url": "https://github.com/example/neural-network",
        "title": "Neural Network Implementation",
        "description": "A PyTorch implementation of neural networks",
        "category": "github"
      },
      {
        "url": "https://arxiv.org/abs/2024.12345",
        "title": "Advances in Neural Network Architecture",
        "description": "Research paper on neural network improvements",
        "category": "research"
      }
    ]
  }
}
```

## Examples

### Search News

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "openai",
    "sources": ["news"],
    "limit": 5
  }'
```

### Search Images

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "jupiter",
    "sources": ["images"],
    "limit": 8
  }'
```

## HD Image Search with Size Filtering

Use Google Images operators to find high-resolution images:

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "sunset imagesize:1920x1080",
    "sources": ["images"],
    "limit": 5
  }'
```

```bash
curl -X POST https://api.firecrawl.dev/v2/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fc-YOUR_API_KEY" \
  -d '{
    "query": "mountain wallpaper larger:2560x1440",
    "sources": ["images"],
    "limit": 8
  }'
```

Common HD resolutions:

- `imagesize:1920x1080` - Full HD (1080p)
- `imagesize:2560x1440` - QHD (1440p)
- `imagesize:3840x2160` - 4K UHD
- `larger:1920x1080` - HD and above
- `larger:2560x1440` - QHD and above

## Search with Content Scraping

Search and retrieve content from the search results in one operation.

```typescript
import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR_API_KEY' });

// Search and scrape content
const results = await firecrawl.search({
  query: 'firecrawl web scraping',
  limit: 3,
  scrapeOptions: {
    formats: ['markdown', 'links']
  }
});
```

Every option in scrape endpoint is supported by this search endpoint through the `scrapeOptions` parameter.

### Response with Scraped Content

```json
{
  "success": true,
  "data": [
    {
      "title": "Firecrawl - The Ultimate Web Scraping API",
      "description": "Firecrawl is a powerful web scraping API that turns any website into clean, structured data for AI and analysis.",
      "url": "https://firecrawl.dev/",
      "markdown": "# Firecrawl\\n\\nThe Ultimate Web Scraping API\\n\\n## Turn any website into clean, structured data\\n\\nFirecrawl makes it easy to extract data from websites for AI applications, market research, content aggregation, and more...",
      "links": [
        "https://firecrawl.dev/pricing",
        "https://firecrawl.dev/docs",
        "https://firecrawl.dev/guides"
      ],
      "metadata": {
        "title": "Firecrawl - The Ultimate Web Scraping API",
        "description": "Firecrawl is a powerful web scraping API that turns any website into clean, structured data for AI and analysis.",
        "sourceURL": "https://firecrawl.dev/",
        "statusCode": 200
      }
    }
  ]
}
```

## Advanced Search Options

Firecrawl's search API supports various parameters to customize your search.

### Location Customization

```typescript
import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR_API_KEY' });

// Search with location settings (Germany)
const searchResult = await firecrawl.search({
  query: 'web scraping tools',
  limit: 5,
  location: 'Germany'
});

// Process the results
for (const result of searchResult.data) {
  console.log(`Title: ${result.title}`);
  console.log(`URL: ${result.url}`);
}
```

### Time-Based Search

Use the `tbs` parameter to filter results by time:

```typescript
import Firecrawl from '@mendable/firecrawl-js';

const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR-API-KEY' });

const results = await firecrawl.search({
  query: 'firecrawl',
  limit: 5,
  tbs: 'qdr:d'
});
console.log(results.data?.web?.length || 0);
```

Common `tbs` values:

- `qdr:h` - Past hour
- `qdr:d` - Past 24 hours
- `qdr:w` - Past week
- `qdr:m` - Past month
- `qdr:y` - Past year

For more precise time filtering, you can specify exact date ranges using the custom date range format:

```typescript
import Firecrawl from '@mendable/firecrawl-js';

// Initialize the client with your API key
const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR_API_KEY' });

// Search for results from December 2024
const searchResult = await firecrawl.search({
  query: 'firecrawl updates',
  limit: 10,
  tbs: 'cdr:1,cd_min:12/1/2024,cd_max:12/31/2024'
});
```

### Custom Timeout

Set a custom timeout for search operations:

```typescript
import Firecrawl from '@mendable/firecrawl-js';

// Initialize the client with your API key
const firecrawl = new Firecrawl({ apiKey: 'fc-YOUR_API_KEY' });

// Set a 30-second timeout
const searchResult = await firecrawl.search({
  query: 'complex search query',
  limit: 10,
  timeout: 30000  // 30 seconds in milliseconds
});
```

## Cost Implications

When search results are not scraped (no scrape options specified), the cost is **2 credits per 10 search results**. When scraping is enabled, there is no additional charge for basic scrapes of each search result beyond the standard scraping costs.

However, be aware of these cost factors:

- **PDF parsing**: 1 credit per PDF page (can significantly increase costs for multi-page PDFs)
- **Stealth proxy mode**: +4 additional credits per search result
- **JSON mode**: +4 additional credits per search result

To control costs:

- Set `parsers: []` if you don't need PDF content
- Use `proxy: 'basic'` instead of `'stealth'` when possible
- Limit the number of search results with the `limit` parameter

## Advanced Scraping Options

For more details about the scraping options, refer to the Scrape Feature documentation. Everything except for the FIRE-1 Agent and Change-Tracking features are supported by this Search endpoint.

