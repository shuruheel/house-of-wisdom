export interface Message {
    id: string;
    text: string;
    sender: 'user' | 'ai';
    mermaidDiagrams?: MermaidDiagram[];
  }
  
  export interface Conversation {
    id: string;
    name: string;
    messages: Message[];
  }

  export interface Event {
    name?: string;
    description?: string;
    emotion?: string;
    start_date?: string;
    concepts?: number;
    concept_relationships?: number;
    [key: string]: any;
  }
  
  export interface Claim {
    content?: string;
    source?: string;
    [key: string]: any;
  }

  export interface ConversationTurn {
    text: string;
    response: string;
    mermaidDiagrams?: MermaidDiagram[];
  }

  export interface ChainOfThoughtQuestion {
    question: string;
    reasoning_types: string[];
  }

  export interface MermaidDiagram {
    question: string;
    diagram: string;
  }

  export interface LegalInfoContext {
    provisions: {
      content: string;
      section_number: string;
      chapter_number: string;
      title_number: string;
      similarity: number;
    }[];
    articles: {
      content: string;
      title: string;
      similarity: number;
    }[];
    amendments: {
      content: string;
      title: string;
      similarity: number;
    }[];
    relationships: {
      related_entities: string[];
      related_concepts: string[];
    };
    comparisons: {
      amendment: {
        content: string;
        title: string;
        similarity: number;
      };
      provision: {
        content: string;
        section_number: string;
        chapter_number: string;
        title_number: string;
        similarity: number;
      };
    }[];
  }