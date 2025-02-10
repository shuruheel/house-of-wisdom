import OpenAI from 'openai';
import { config } from '../config';
import fs from 'fs/promises';
import path from 'path';
import NodeCache from 'node-cache';
import { handleError } from '../utils/errorHandler';

const openai = new OpenAI({ apiKey: config.openAI.apiKey });

const embeddingCache = new NodeCache({ stdTTL: 3600 }); // Cache for 1 hour

let chunkEmbeddings: { [key: string]: number[] } | null = null;

export async function computeQueryEmbedding(query: string): Promise<number[]> {
  try {
    const cacheKey = `embedding:${query}`;
    const cachedEmbedding = embeddingCache.get<number[]>(cacheKey);
    
    if (cachedEmbedding) {
      return cachedEmbedding;
    }

    const response = await openai.embeddings.create({
      model: 'text-embedding-3-large',
      input: query,
    });
    
    const embedding = response.data[0].embedding;
    embeddingCache.set(cacheKey, embedding);
    
    return embedding;
  } catch (error) {
    throw handleError(error, 'computeQueryEmbedding');
  }
}

async function loadChunkEmbeddings(): Promise<{ [key: string]: number[] }> {
  if (!chunkEmbeddings) {
    const embeddingsPath = path.join(process.cwd(), 'chunk_embeddings.json');
    const embeddingsData = await fs.readFile(embeddingsPath, 'utf-8');
    chunkEmbeddings = JSON.parse(embeddingsData);
  }
  return chunkEmbeddings!;
}

export async function getRelevantChunks(query: string, queryEmbedding: any[], topN = 1, similarityThreshold = 0.35): Promise<any[]> {
  const embeddings = await loadChunkEmbeddings();

  const relevantChunks = [];

  for (const [chunkPath, chunkEmbedding] of Object.entries(embeddings)) {
    const similarity = cosineSimilarity(queryEmbedding, chunkEmbedding);

    if (similarity >= similarityThreshold) {
      const txtPath = chunkPath.replace('.json', '.txt');
      try {
        const chunkContent = await fs.readFile(txtPath, 'utf-8');
        relevantChunks.push({
          path: txtPath,
          content: chunkContent,
          similarity,
        });
      } catch (error) {
        console.warn(`TXT file not found: ${txtPath}`);
      }
    }
  }

  relevantChunks.sort((a, b) => b.similarity - a.similarity);
  return relevantChunks.slice(0, topN);
}

function cosineSimilarity(a: number[], b: number[]): number {
  const dotProduct = a.reduce((sum, _, i) => sum + a[i] * b[i], 0);
  const magnitudeA = Math.sqrt(a.reduce((sum, val) => sum + val * val, 0));
  const magnitudeB = Math.sqrt(b.reduce((sum, val) => sum + val * val, 0));
  return dotProduct / (magnitudeA * magnitudeB);
}