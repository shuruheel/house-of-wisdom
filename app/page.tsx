'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { PlusCircle, Save, Trash2, Send } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { Message, Conversation } from './types'

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
        updateConversationName(activeConversation.id, newName);
        try {
          const response = await fetch('/api/conversation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: activeConversation.id, name: newName, messages: activeConversation.messages }),
          });
          if (response.ok) {
            const updatedConversation = await response.json();
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

  const handleClearConversation = () => {
    setConversations(prevConversations => prevConversations.map(conv =>
      conv.id === activeConversationId ? { ...conv, messages: [] } : conv
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
            if (done) break;
            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                aiMessage.text += data.chunk;
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

  const handleDeleteConversation = () => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      setConversations(prevConversations => prevConversations.filter(conv => conv.id !== activeConversationId));
      if (conversations.length > 1) {
        setActiveConversationId(conversations.find(conv => conv.id !== activeConversationId)?.id || '');
      } else {
        handleNewConversation();
      }
    }
  };

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
                variant={activeConversationId === conv.id ? "secondary" : "ghost"}
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
                  <div className={`max-w-[80%] rounded-lg p-3 ${
                    message.sender === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
                  }`}>
                    {message.sender === 'ai' ? (
                      <ReactMarkdown 
                        rehypePlugins={[rehypeRaw, rehypeSanitize]}
                        components={{
                          p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-none pl-5 mb-4 last:mb-0" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-4 last:mb-0" {...props} />,
                          li: ({node, ...props}) => <li className="mb-1" {...props} />
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