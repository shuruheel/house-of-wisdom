import dotenv from 'dotenv';

dotenv.config();

export const config = {
  neo4j: {
    uri: process.env.NEO4J_URI,
    user: process.env.NEO4J_USER,
    password: process.env.NEO4J_PASSWORD,
    database: process.env.NEO4J_DATABASE,
  },
  openAI: {
    apiKey: process.env.OPENAI_API_KEY,
  },
  google: {
    apiKey: process.env.GOOGLE_API_KEY,
  },
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY,
  },
  groq: {
    apiKey: process.env.GROQ_API_KEY,
  },
};