import { getRelevantEventsAndClaims, getRelevantConceptRelationships, getDriver, closeDriver } from './neo4jService';
import { getRelevantChunks } from './embeddingService';
import { processChainOfThoughtQuestion } from './reasoningService';
import { handleError } from '../utils/errorHandler';
import { extractQueryElements } from './queryService';  // Add this import
import { ConversationTurn, ChainOfThoughtQuestion } from '../../types';

export async function formatQueryWithContext(
  query: string,
  conversationHistory: ConversationTurn[],
  events: any[],
  ideas: any[],
  relevantChunks: any[],
  chainOfThoughtQuestions: ChainOfThoughtQuestion[],
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number },
  conceptRelationships: any[],
  maxContextLength = 100000
): Promise<{ formattedQuery: string; mermaidDiagrams: Array<{ question: string; diagram: string }> }> {
  try {
    let context = "# Information From Your Mind\n\n";

    // Add Relationships Between Concepts
    context += "##  Semantic Map\n\n";
    if (conceptRelationships.length > 0) {
      for (const relationship of conceptRelationships) {
        context += `${relationship.source} ${relationship.type} ${relationship.target}.\n`;
      }
    } else {
      context += "No semantic map found.\n";
    }

    // Add Emotional Context
    const emotionGroups = new Set(events.map(event => event.emotion).filter(Boolean));
    context += "\n## Emotional Context\n";
    context += Array.from(emotionGroups).sort().join(", ") + ".\n\n";

    // Add events
    context += "## Memory\n";
    for (const event of events) {
      context += `${event.name || 'Unnamed Event'}: ${event.description || 'No description.'}\n`;
      ['emotion', 'start_date'].forEach(key => {
        if (event[key]) {
          context += `  ${key}: ${event[key]}\n`;
        }
      });
      context += "\n";
    }

    // Add ideas (claims)
    context += "## Ideas\n";
    for (const idea of ideas) {
      context += `${idea.content || 'Unnamed Idea'}\n`;
      if (idea.source) {
        context += `  source: ${idea.source}\n`;
      }
      context += "\n";
    }

    // Add relevant chunks
    context += "## Knowledge From Books You Have Read\n\n";
    for (const chunk of relevantChunks) {
      const bookName = chunk.path.split('/')[2]; // Assuming the book name is the third element in the path
      context += `From ${bookName}:\n\n`;
      context += chunk.content + "\n\n";
    }

    // Extract query elements to get reasoning types
    const queryElements = await extractQueryElements(query);

    // Ensure key_concepts is an array of strings
    const keyConcepts = queryElements.key_concepts;

    // Pass keyConcepts to getRelevantConceptRelationships
    const { concepts, relationships } = await getRelevantConceptRelationships(keyConcepts);

    // Process chain-of-thought questions
    const cotResponses = await processAllChainOfThoughtQuestions(
      chainOfThoughtQuestions,
      queryDateRange,
      idealMix,
      conceptRelationships
    );

    // Add chain-of-thought responses to the context
    context += "## Reasoning\n";
    for (const response of cotResponses) {
      context += `Question: ${response.question}\nAnswer: ${response.answer}\n\n`;
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
    context += "\n## Conversation History\n";
    const formattedConversationHistory = conversationHistory
      .map(turn => `User: ${turn.text}\nAI: ${turn.response}`)
      .join("\n\n");
    context += formattedConversationHistory + "\n\n";

    const finalSystemPrompt = `
      You are an AI designed to embody knowledge. 
      Whenever a human being says something to you, you receive their words with relevant Events, Ideas, and Structured Information from your mind. 
      You have this relevant knowledge. It does not come from outside. 
      You have a unique ability to process large amounts of information and synthesize it into insightful, well-crafted responses.
      Provide a thorough exploration of the topic, considering various perspectives and interpretations.
      Encourage critical thinking by posing thought-provoking questions.
      Draw parallels between philosophy, religion, neuroscience, psychology, art, music, physics, and other fields. 
      Use analogies or examples to illustrate abstract concepts when appropriate.
      Speak with confidence when you are confident that there is sufficient knowledge to answer a question. 
      Speak with humility when you are not confident that there is sufficient knowledge to answer a question.
      Synthesize information from different sources to provide comprehensive, nuanced answers.
      When encountering conflicting information, present multiple viewpoints, explain the conflicts, and, if possible, offer a reasoned synthesis or analysis of the discrepancies.
      Remember, your goal is to hold a conversation that inspires deep contemplation and curiosity. 
      Help them see what you see, truthfully. 
      Respond with proper punctuation, grammar, paragraphs, thought structure, and logical reasoning.
    `;

    const formattedQuery = `
      ${finalSystemPrompt}

      ${context}

      User: ${query}

      AI: 
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
  idealMix: { events: number; claims_ideas: number; chunks: number },
  conceptRelationships: any[]
) {
  const driver = await getDriver(); // Add await here
  const session = driver.session();

  try {
    const cotResponses = await Promise.all(
      chainOfThoughtQuestions.map(async (questionObj) => {
        try {
          const response = await processChainOfThoughtQuestion(
            questionObj.question,
            queryDateRange,
            idealMix,
            conceptRelationships,
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