# House of Wisdom

House of Wisdom is an advanced AI-powered conversational application built with Next.js. It leverages various AI models and services to provide insightful, context-aware responses to user queries.

## Features

- AI-powered conversations with context-aware responses
- Support for multiple AI providers (OpenAI, Google, Anthropic, Groq)
- Dynamic rendering of Mermaid diagrams for visual explanations
- Conversation history management
- Responsive UI with light and dark mode support

## Technologies Used

- Next.js 13+ (App Router)
- React
- TypeScript
- Tailwind CSS
- Shadcn UI Components
- Mermaid.js for diagram rendering
- Neo4j for graph database (knowledge representation)
- Various AI APIs (OpenAI, Google AI, Anthropic, Groq)

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up environment variables:
   Create a `.env.local` file in the root directory and add the following variables:
   ```
   NEO4J_URI=your_neo4j_uri
   NEO4J_USER=your_neo4j_user
   NEO4J_PASSWORD=your_neo4j_password
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_API_KEY=your_google_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GROQ_API_KEY=your_groq_api_key
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Project Structure

- `app/`: Main application code
  - `components/`: React components
  - `lib/`: Utility functions and services
  - `api/`: API routes
  - `types/`: TypeScript type definitions
- `public/`: Static assets
- `conversation_histories/`: Stored conversation data

## Key Components

1. Main Chat Interface: