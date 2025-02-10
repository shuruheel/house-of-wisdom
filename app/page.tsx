'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { PlusCircle, Save, Trash2, Send, Eye, EyeOff } from 'lucide-react'
import { Button } from "./components/ui/button"
import { Input } from "./components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "./components/ui/card"
import { ScrollArea } from "./components/ui/scroll-area"
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { Message, Conversation } from './types'
import MermaidDiagramRenderer from './components/MermaidDiagramRenderer'
import { useHotkeys } from 'react-hotkeys-hook';

const defaultConversation: Conversation = {
  id: uuidv4(),
  name: 'New Conversation',
  messages: []
};

export default function Home() {
  const [conversations, setConversations] = useState<Conversation[]>([defaultConversation]);
  const [activeConversationId, setActiveConversationId] = useState<string>(defaultConversation.id);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hiddenDiagrams, setHiddenDiagrams] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeConversation = conversations.find(conv => conv.id === activeConversationId) ?? defaultConversation;

  const fetchConversations = useCallback(async () => {
    try {
      const response = await fetch('/api/conversations');
      if (response.ok) {
        const data = await response.json();
        if (data.length > 0) {
          setConversations(data);
          setActiveConversationId(data[0].id);
        }
      } else {
        console.error('Failed to fetch conversations');
      }
    } catch (error) {
      console.error('Error fetching conversations:', error);
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  };

  const handleNewConversation = () => {
    const newConversation: Conversation = { id: uuidv4(), name: 'New Conversation', messages: [] };
    setConversations(prevConversations => [...prevConversations, newConversation]);
    setActiveConversationId(newConversation.id);
  };

  const handleSaveConversation = async () => {
    if (activeConversation) {
      const newName = prompt('Enter a name for the conversation:', activeConversation.name);
      if (newName) {
        const updatedConversation = { ...activeConversation, name: newName };
        try {
          const response = await fetch('/api/conversation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedConversation),
          });

          if (response.ok) {
            setConversations(prevConversations => prevConversations.map(conv =>
              conv.id === updatedConversation.id ? updatedConversation : conv
            ));
          } else {
            console.error('Failed to save conversation');
          }
        } catch (error) {
          console.error('Error saving conversation:', error);
        }
      }
    }
  };

  const updateConversationName = (id: string, name: string) => {
    setConversations(prevConversations => prevConversations.map(conv =>
      conv.id === id ? { ...conv, name } : conv
    ));
  };

  const handleSendMessage = async () => {
    if (input.trim() && activeConversation) {
      const newMessage: Message = { id: uuidv4(), text: input, sender: 'user' };
      setConversations(prevConversations => prevConversations.map(conv =>
        conv.id === activeConversationId
          ? { ...conv, messages: [...(conv.messages || []), newMessage] }
          : conv
      ));
      setInput('');
      setIsLoading(true);

      try {
        const response = await fetch('/api/conversation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: input, conversationId: activeConversationId }),
        });

        if (!response.ok) {
          throw new Error('Network response was not ok');
        }

        const reader = response.body?.getReader();
        let aiMessage: Message = { id: uuidv4(), text: '', sender: 'ai' };

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              console.log('Stream finished');
              break;
            }
            const chunk = new TextDecoder().decode(value);
            console.log('Received chunk:', chunk);
            const lines = chunk.split('\n\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                console.log('Parsed data:', data);
                if (data.chunk) {
                  aiMessage.text += data.chunk;
                  console.log('Updated AI message:', aiMessage.text);
                } else if (data.mermaidDiagrams) {
                  aiMessage.mermaidDiagrams = data.mermaidDiagrams;
                  console.log('Received mermaid diagrams:', data.mermaidDiagrams);
                }
                setConversations(prevConvs => prevConvs.map(conv =>
                  conv.id === activeConversationId
                    ? { ...conv, messages: [...(conv.messages || []).filter(m => m.id !== aiMessage.id), aiMessage] }
                    : conv
                ));
              }
            }
          }
        }
      } catch (error) {
        console.error('Error sending message:', error);
        setConversations(prevConversations => prevConversations.map(conv =>
          conv.id === activeConversationId
            ? { ...conv, messages: [...(conv.messages || []), { id: uuidv4(), text: 'Error: Failed to get AI response. Please try again.', sender: 'ai' }] }
            : conv
        ));
      } finally {
        setIsLoading(false);
        scrollToBottom();
      }
    }
  };

  const handleDeleteConversation = useCallback(async () => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      try {
        // Make an API call to delete the conversation from the server
        const response = await fetch(`/api/conversation?id=${activeConversationId}`, {
          method: 'DELETE',
        });

        if (!response.ok) {
          throw new Error('Failed to delete conversation');
        }

        // If the deletion was successful on the server, update the local state
        setConversations(prevConversations => {
          const updatedConversations = prevConversations.filter(conv => conv.id !== activeConversationId);
          
          if (updatedConversations.length > 0) {
            // Find the next conversation to set as active
            const nextConversation = updatedConversations.find(conv => conv.id !== activeConversationId) || updatedConversations[0];
            setActiveConversationId(nextConversation.id);
          } else {
            // If no conversations left, create a new one
            const newConversation = { id: uuidv4(), name: 'New Conversation', messages: [] };
            setActiveConversationId(newConversation.id);
            return [newConversation];
          }
          
          return updatedConversations;
        });
      } catch (error) {
        console.error('Error deleting conversation:', error);
        alert('Failed to delete conversation. Please try again.');
      }
    }
  }, [activeConversationId]);

  const toggleDiagramVisibility = (messageId: string) => {
    setHiddenDiagrams(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  const handleKeyNavigation = useCallback((direction: 'up' | 'down') => {
    const currentIndex = conversations.findIndex(conv => conv.id === activeConversationId);
    let newIndex;

    if (direction === 'up') {
      newIndex = currentIndex > 0 ? currentIndex - 1 : conversations.length - 1;
    } else {
      newIndex = currentIndex < conversations.length - 1 ? currentIndex + 1 : 0;
    }

    setActiveConversationId(conversations[newIndex].id);
  }, [conversations, activeConversationId]);

  useHotkeys('up', () => handleKeyNavigation('up'), { enableOnFormTags: ['INPUT'] });
  useHotkeys('down', () => handleKeyNavigation('down'), { enableOnFormTags: ['INPUT'] });

  return (
    <div className="flex h-screen bg-background">
      <aside className="w-64 bg-card border-r overflow-hidden flex flex-col">
        <div className="p-4 flex-shrink-0">
          <h1 className="text-2xl font-bold mb-4 text-primary">House of Wisdom</h1>
          <Button onClick={handleNewConversation} className="w-full mb-4">
            <PlusCircle className="mr-2 h-4 w-4" /> New Conversation
          </Button>
        </div>
        <ScrollArea className="flex-grow">
          <div className="p-4 space-y-2">
            {conversations.map(conv => (
              <Button
                key={conv.id}
                variant={activeConversationId === conv.id ? "default" : "secondary"}
                className="w-full justify-start"
                onClick={() => setActiveConversationId(conv.id)}
              >
                {conv.name}
              </Button>
            ))}
          </div>
        </ScrollArea>
      </aside>
      <main className="flex-1 flex flex-col overflow-hidden">
        <Card className="flex flex-col h-full m-4 overflow-hidden">
          <CardHeader className="flex-shrink-0 flex flex-row items-center justify-between">
            <CardTitle>{activeConversation?.name || 'New Conversation'}</CardTitle>
            <div className="flex space-x-2">
              <Button size="icon" variant="outline" onClick={handleSaveConversation}>
                <Save className="h-4 w-4" />
                <span className="sr-only">Save Conversation</span>
              </Button>
              <Button size="icon" variant="outline" onClick={handleDeleteConversation}>
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Delete Conversation</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex-grow overflow-hidden p-4">
            <ScrollArea className="h-full pr-4" ref={scrollRef}>
              {activeConversation?.messages?.map((message) => (
                <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
                  <div className={`max-w-[80%] rounded-lg p-3 relative ${
                    message.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
                  }`}>
                    {message.sender === 'ai' && message.mermaidDiagrams && message.mermaidDiagrams.length > 0 && (
                      <div className="mb-5">
                      <button 
                        onClick={() => toggleDiagramVisibility(message.id)}
                        className="absolute top-1 left-1 p-1 rounded-full bg-background/50 hover:bg-background/75 transition-colors"
                      >
                        
                        {hiddenDiagrams.has(message.id) ? (
                          <Eye className="h-4 w-4" />
                        ) : (
                          <EyeOff className="h-4 w-4" />
                        )}
                      </button>
                      </div>
                    )}
                    {message.sender === 'ai' && message.mermaidDiagrams && message.mermaidDiagrams.length > 0 && !hiddenDiagrams.has(message.id) && (
                      <div className="mb-4">
                        <MermaidDiagramRenderer diagrams={message.mermaidDiagrams} />
                      </div>
                    )}
                    {message.sender === 'ai' ? (
                      <ReactMarkdown 
                        rehypePlugins={[rehypeRaw, rehypeSanitize]}
                        components={{
                          p: ({node, ...props}) => <p className="mb-3 last:mb-0" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-none pl-5 mb-2 last:mb-0" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-2 last:mb-0" {...props} />,
                          li: ({node, ...props}) => <li className="mb-1" {...props} />,
                          h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-6" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-4" {...props} />,
                          h3: ({node, ...props}) => <h3 className="text-lg font-semibold mb-2" {...props} />,
                          h4: ({node, ...props}) => <h3 className="text-lg font-medium mb-2" {...props} />,
                          strong: ({node, ...props}) => <b className="font-medium" {...props} />
                        }}
                      >
                        {message.text}
                      </ReactMarkdown>
                    ) : (
                      message.text
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start mb-4">
                  <div className="max-w-[80%] w-full">
                    <div className="h-4 bg-secondary rounded animate-pulse mb-2"></div>
                    <div className="h-4 bg-secondary rounded animate-pulse w-5/6 mb-2"></div>
                    <div className="h-4 bg-secondary rounded animate-pulse w-4/6"></div>
                  </div>
                </div>
              )}
            </ScrollArea>
          </CardContent>
          <CardFooter className="flex-shrink-0 bg-card border-t p-4">
            <div className="flex w-full space-x-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
              />
              <Button onClick={handleSendMessage} disabled={isLoading}>
                <Send className="h-4 w-4" />
                <span className="sr-only">Send Message</span>
              </Button>
            </div>
          </CardFooter>
        </Card>
      </main>
    </div>
  );
}