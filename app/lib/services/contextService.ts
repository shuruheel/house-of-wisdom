import { getRelevantEventsAndClaims, getRelevantConceptRelationships, getDriver, closeDriver, getRelevantLegalReferences } from './neo4jService';
import { processChainOfThoughtQuestion } from './reasoningService';
import { handleError } from '../utils/errorHandler';
import { ConversationTurn, ChainOfThoughtQuestion } from '../../types';
import { int } from 'neo4j-driver';

export async function formatQueryWithContext(
  query: string,
  queryEmbedding: any[],
  conversationHistory: ConversationTurn[],
  legal_question: string | "no",
  relevantChunks: any[],
  chainOfThoughtQuestions: ChainOfThoughtQuestion[],
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number; concept_relationships: number }
  ): Promise<{ formattedQuery: string; mermaidDiagrams: Array<{ question: string; diagram: string }> }> {
  try {
    let context = "# Relevant Knowledge\n\n";

    // Add relevant chunks
    context += "## Books\n\n";
    for (const chunk of relevantChunks) {
      const bookName = chunk.path.split('/')[2]; // Assuming the book name is the third element in the path
      context += `From ${bookName}:\n\n`;
      context += `[Book Excerpt] ${chunk.content}\n\n`;
    }

    // Always fetch concept relationships
    const conceptRelationships = await getRelevantConceptRelationships(
      queryEmbedding,
      int(idealMix.concept_relationships),
      0.3
    );

    context += "## Concepts and Relationships\n";
    for (const relationship of conceptRelationships.relationships) {
      context += `${relationship.source} ${relationship.type} ${relationship.target}\n`;
    }
    context += "\n";

    const { events, claims } = await getRelevantEventsAndClaims(
      queryEmbedding,
      idealMix.events,
      idealMix.claims_ideas,
      0.3,
      queryDateRange
    );
    
    // Add events to context
    context += "## Events\n";
    for (const event of events) {
      context += `${event.name || 'Unnamed Event'}: ${event.description || 'No description.'}\n`;
      const eventFields = ['emotion', 'start_date'];
      for (const key of eventFields) {
        if (event[key] !== undefined) {
          context += `  ${key}: ${event[key]}\n`;
        }
      }
      context += "\n";
    }

    // Add claims/ideas to context
    context += "## Ideas\n";
    for (const claim of claims) {
      context += `${claim.content || 'No content'}\n`;
      const ideaFields = ['source'];
      for (const key of ideaFields) {
        if (claim[key] !== undefined) {
          context += `  ${key}: ${claim[key]}\n`;
        }
      }
      context += "\n";
    }

    if (legal_question === "yes") {
      // const cypherQuery = await generateCypherQuery(query);
      const queryResults = await getRelevantLegalReferences(queryEmbedding, 0.3, int(13));

      const MAX_ITEMS = 27; // Set the maximum number of items to include
      let itemCount = 0;
      let legalInfoContext = '## Legal References\n\n';
      const uniqueItems = new Set();

      for (const item of queryResults) {
        if (itemCount >= MAX_ITEMS) break; // Stop if we've reached the limit
        
        const resultKey = Object.keys(item).find(key => key.includes('result'));
        if (!resultKey) continue;
        
        const result = item[resultKey];
        
        // Create a unique key for the item based on its content
        const uniqueKey = `${result.type}:${result.content}`;
        
        // Only process the item if it's not already in the set
        if (!uniqueItems.has(uniqueKey)) {
          uniqueItems.add(uniqueKey);
          
          if (result.type === 'Provision') {
            legalInfoContext += `${result.type}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
            legalInfoContext += `  ${result.chapter_number || ''}: ${result.section_number || ''} ${result.section_title || ''}\n`;
          } else if (result.type === 'Amendment') {
            legalInfoContext += `${result.title || ''}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
          } else if (result.type === 'Article') {
            legalInfoContext += `${result.title || ''}:\n`;
            legalInfoContext += `  ${result.content || ''}\n`;
          }

          legalInfoContext += "\n";
          itemCount++; // Increment the counter after processing a unique item
        }
      }
      console.log("Legal Information Context:", legalInfoContext);
      context += legalInfoContext;

    }

    // Process chain-of-thought questions
    const cotResponses = await processAllChainOfThoughtQuestions(
      chainOfThoughtQuestions,
      queryDateRange,
      idealMix,
      query,
      legal_question
    );

    // Add chain-of-thought responses to the context
    context += "## Chain of Thought\n";
    for (const response of cotResponses) {
      context += `${response.answer}\n\n`;
    }

    // Extract Mermaid diagrams from cotResponses, cleaning up markdown syntax
    const mermaidDiagrams = cotResponses.flatMap(response => {
      const mermaidMatches = response.answer.match(/```mermaid\s*([\s\S]*?)\s*```/g) || [];
      return mermaidMatches.map(match => {
        const diagramContent = match.replace(/```mermaid\s*|\s*```/g, '').trim();
        return {
          question: response.question,
          diagram: diagramContent
        };
      });
    });

    // Add conversation history to the context
    context += "\n## Conversation History\n\n";
    const formattedConversationHistory = conversationHistory
      .map(turn => `User: ${turn.text}\nAI: ${turn.response}`)
      .join("\n\n");
    context += formattedConversationHistory + "\n\n";

    const formattedQuery = `

      ${context}
      
      The user says:
      ${query}

      Your response:
      
    `;

    console.debug(`Formatted query length: ${formattedQuery.length} characters`);
    return { formattedQuery, mermaidDiagrams };
  } catch (error) {
    throw handleError(error, 'formatQueryWithContext');
  }
}

async function processAllChainOfThoughtQuestions(
  chainOfThoughtQuestions: ChainOfThoughtQuestion[],
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number; concept_relationships: number },
  originalQuery: string,
  legal_question: string | "no"
) {
  const driver = await getDriver();
  const session = driver.session();

  try {
    // Add the original query to the chainOfThoughtQuestions
    const allQuestions = [
      { question: originalQuery, reasoning_types: [] },
      ...chainOfThoughtQuestions
    ];

    const cotResponses = await Promise.all(
      chainOfThoughtQuestions.map(async (questionObj) => {
        try {
          const response = await processChainOfThoughtQuestion(
            questionObj.question,
            legal_question,
            queryDateRange,
            idealMix,
            questionObj.reasoning_types,
            session
          );
          return {
            question: questionObj.question,
            answer: response
          };
        } catch (error) {
          console.error(`Error processing chain-of-thought question: ${questionObj.question}`, error);
          throw error;
        }
      })
    );

    return cotResponses;
  } finally {
    await session.close();
  }
}

// Ensure to close the driver when the application shuts down
process.on('exit', async () => {
  await closeDriver();
});