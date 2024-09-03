import { generateText } from './aiService';
import { computeQueryEmbedding } from './embeddingService';
import { getDriver, getRelevantEventsAndClaims } from './neo4jService';
import { Event, Claim } from '../../types';

export async function processChainOfThoughtQuestion(
  question: string,
  queryDateRange: string | null,
  idealMix: { events: number; claims_ideas: number; chunks: number },
  conceptRelationships: any[],
  reasoningTypes: string[],
  session: any // Pass the session as a parameter
): Promise<string> {
  if (typeof question !== 'string') {
    throw new Error(`Invalid question type: ${typeof question}. Expected a string.`);
  }

  console.info(`Starting to process chain-of-thought question: ${question}`);

  const systemPrompt = `
    # Role
    You are an artificial intelligence well-trained to apply reasoning to questions and visualize the reasoning using Mermaid diagrams. 

    # Guidelines
    Use appropriate shapes for different elements.
    Employ clear and concise labels for each node.
    Use arrows to show the flow of logic or sequence of events.
    Incorporate branching paths to represent different outcomes or possibilities.
    Use color coding to depict emotions. 

    # Deductive Reasoning
        graph TD
        A[Premise 1: Conflicts involve multiple actors and forms of tension]
        B[Premise 2: Information details specific incidents and ongoing conflicts]
        C[Conclusion: Major areas of conflict can be categorized by actors and nature]
        
        A --> C
        B --> C
        
        C --> D[Categorization of Conflicts]
        D --> E[By Actors Involved]
        D --> F[By Nature of Conflict]
        
        E --> G[State vs State]
        E --> H[State vs Non-State Actors]
        E --> I[Internal Conflicts]
        
        F --> J[Military Clashes]
        F --> K[Political Tensions]
        F --> L[Economic Issues]

    # Inductive Reasoning
        graph TD
          A[Analysis of Specific Incidents and Patterns]
          A --> B[Israel-Hezbollah Conflict]
          A --> C[Israel-Palestine Tensions]
          A --> D[Iran-Israel Tensions]
          A --> E[Regional Maritime Security]
          A --> F[Syria Conflict]
          A --> G[Internal Israeli Political Tensions]
          A --> H[Egypt-Ethiopia Tensions]
          A --> I[Lebanon's Internal Crisis]
          A --> J[Turkey's Regional Involvement]
          A --> K[U.S. Involvement in Regional Conflicts]
          
          L[Inferred Major Areas of Conflict/Tension]
          B --> L
          C --> L
          D --> L
          E --> L
          F --> L
          G --> L
          H --> L
          I --> L
          J --> L
          K --> L

    # Abstract Reasoning
        graph TD
          A[Identify Patterns in Regional Conflicts]
          A --> B[Power Dynamics]
          A --> C[Resource Control]
          A --> D[Ideological Differences]
          A --> E[Historical Grievances]
          
          F[Abstract Concepts Underlying Conflicts]
          B --> F
          C --> F
          D --> F
          E --> F
          
          F --> G[Sovereignty Disputes]
          F --> H[Religious Tensions]
          F --> I[Economic Inequalities]
          F --> J[Geopolitical Interests]

    # Abductive Reasoning
        graph TD
          A[Observation: Multiple Ongoing Conflicts in Region]
          A --> B[Hypothesis 1: Historical Unresolved Issues]
          A --> C[Hypothesis 2: External Power Interference]
          A --> D[Hypothesis 3: Resource Scarcity]
          A --> E[Hypothesis 4: Ideological Differences]
          
          F[Best Explanation for Regional Tensions]
          B --> F
          C --> F
          D --> F
          E --> F

    # Analogical Reasoning
        graph TD
          A[Source: Historical Conflicts]
          B[Target: Current Regional Tensions]
          
          A --> C[Shared Features]
          B --> C
          
          C --> D[Territorial Disputes]
          C --> E[Ethnic/Religious Divisions]
          C --> F[Resource Competition]
          C --> G[Power Imbalances]
          
          H[Inferred Similarities in Conflict Dynamics]
          D --> H
          E --> H
          F --> H
          G --> H

    # Causal Reasoning
        graph TD
          A[Root Causes]
          A --> B[Historical Borders]
          A --> C[Religious Differences]
          A --> D[Economic Disparities]
          A --> E[External Interventions]
          
          F[Intermediate Effects]
          B --> F
          C --> F
          D --> F
          E --> F
          
          G[Current Major Areas of Conflict]
          F --> G
          
          G --> H[Israel-Palestine Conflict]
          G --> I[Iran-Saudi Rivalry]
          G --> J[Syrian Civil War]
          G --> K[Yemen Crisis]

    # Important Instructions
    Do not use parentheses, curly braces, square brackets, and percentage signs in node labels, as these characters are not supported by the Mermaid parser.
  `;

  let context = `## Question: ${question}\n`;
  context += `Apply ${reasoningTypes.join(', ')} reasoning using the following knowledge:\n`;

  try {
    const questionEmbedding = await computeQueryEmbedding(question);
    console.debug(`Computed question embedding for: ${question}`);

    const { events, claims } = await getRelevantEventsAndClaims(
      questionEmbedding,
      idealMix.events,
      idealMix.claims_ideas,
      0.3, // similarityThreshold, you may want to make this configurable
      queryDateRange
      // Removed session parameter
    );

    console.debug(`Retrieved ${events.length} events and ${claims.length} claims for question: ${question}`);

    // Add events to context
    context += "### Events\n";
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
    context += "### Ideas\n";
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

    // Add concept relationships to the context
    context += "##  Semantic Map\n\n";
    if (conceptRelationships.length > 0) {
      for (const relationship of conceptRelationships) {
        context += `${relationship.source} ${relationship.type} ${relationship.target}.\n`;
      }
    } else {
      context += "No relevant concept relationships found.\n";
    }

    context += `\n
      # Your Task
        1. Analyze the following question: ${question}.
        2. Apply the following reasoning types to the question: ${reasoningTypes.join(', ')}.
        3. Generate a Mermaid diagram appropriate for each type of reasoning.
    `;

    // Sanitize and encode the context and system prompt
    console.log('Debug: Context before sanitization:', context);
    console.log('Debug: System prompt before sanitization:', systemPrompt);

    const sanitizedContext = sanitizeString(context);
    const sanitizedSystemPrompt = sanitizeString(systemPrompt);

    console.log('Debug: Sanitized context:', sanitizedContext);
    console.log('Debug: Sanitized system prompt:', sanitizedSystemPrompt);

    const formattedContext = `Question: ${sanitizeString(question)}\n\nContext:\n${sanitizeString(context)}`;
    const formattedSystemPrompt = sanitizeString(systemPrompt);

    let response = '';
    try {
      for await (const chunk of generateText(
        formattedContext,
        formattedSystemPrompt,
        'openai',
        'gpt-4o-mini'
      )) {
        response += chunk;
      }
    } catch (generateTextError) {
      console.error('Error during generateText call:', generateTextError);
      console.log('Debug: Full error object:', JSON.stringify(generateTextError, null, 2));
      throw new Error('Failed to generate text response.');
    }

    console.info(`Finished processing chain-of-thought question: ${question}`);
    return `\n## ${question}\n\n${response}\n`;
  } catch (error) {
    console.error(`Error processing chain-of-thought question: ${question}`, error);
    throw error; // Ensure the error is propagated
  }
}

// Add this helper function at the end of the file
function sanitizeString(input: string): string {
  // Remove any non-printable characters except newlines and tabs
  const sanitized = input.replace(/[^\x20-\x7E\x0A\x09]/g, '');
  
  // Replace any sequences of whitespace (including newlines) with a single space
  return sanitized.replace(/\s+/g, ' ').trim();
}