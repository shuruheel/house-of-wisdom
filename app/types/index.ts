export interface Message {
    id: string;
    text: string;
    sender: 'user' | 'ai';
    mermaidDiagrams?: string[];
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
  }

  export interface ChainOfThoughtQuestion {
    question: string;
    reasoning_types: string[];
  }