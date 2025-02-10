// src/server/config.ts
import dotenv from 'dotenv';

dotenv.config();

export const neo4jConfig = {
  uri: process.env.NEO4J_URI,
  user: process.env.NEO4J_USER,
  password: process.env.NEO4J_PASSWORD,
  database: process.env.NEO4J_DATABASE,
};

export const openAIConfig = {
  apiKey: process.env.OPENAI_API_KEY,
};