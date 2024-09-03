import { NextRequest, NextResponse } from 'next/server';
import { processQuery, loadConversationHistory, saveConversationHistory } from '../../lib/services/conversationService';
import fs from 'fs/promises';
import path from 'path';
import { ConversationTurn } from '../../types';

export async function POST(request: NextRequest) {
  const body = await request.json();
  
  if (body.id && body.name && body.messages) {
    // This is a save request
    return handleSaveConversation(body);
  } else if (body.query && body.conversationId) {
    // This is a query request
    return handleQueryConversation(body);
  } else {
    return new NextResponse(JSON.stringify({ error: 'Invalid request body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

async function handleSaveConversation(conversation: { id: string; name: string; messages: any[] }) {
  const { id, name, messages } = conversation;
  const historyDir = path.join(process.cwd(), 'conversation_histories');
  const filePath = path.join(historyDir, `${id}.json`);

  try {
    await fs.writeFile(filePath, JSON.stringify({ name, messages }));
    return NextResponse.json(conversation);
  } catch (error) {
    console.error('Error saving conversation:', error);
    return NextResponse.json({ error: 'Failed to save conversation' }, { status: 500 });
  }
}

async function handleQueryConversation({ query, conversationId }: { query: string; conversationId: string }) {
  const conversationHistory = await loadConversationHistory(conversationId);
  
  const stream = new ReadableStream({
    async start(controller) {
      const queryGenerator = processQuery(query, conversationHistory);
      let fullResponse = '';
      let mermaidDiagrams: string[] = [];

      try {
        for await (const result of queryGenerator) {
          switch (result.type) {
            case 'chunk':
              controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ chunk: result.content })}\n\n`));
              fullResponse += result.content;
              break;
            case 'mermaidDiagrams':
              mermaidDiagrams = Array.isArray(result.content) ? result.content : [result.content];
              controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ mermaidDiagrams })}\n\n`));
              break;
            case 'error':
              controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ error: result.content })}\n\n`));
              break;
          }
        }
      } catch (error) {
        console.error('Error processing message:', error);
        controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ error: 'An error occurred while processing your message.' })}\n\n`));
      } finally {
        await saveConversationHistory(conversationId, [
          ...conversationHistory,
          { text: query, response: fullResponse, mermaidDiagrams } as ConversationTurn,
        ]);
        controller.close();
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}