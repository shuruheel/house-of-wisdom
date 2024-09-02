import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export async function GET() {
  const historyDir = path.join(process.cwd(), 'conversation_histories');
  
  try {
    const files = await fs.readdir(historyDir);
    const jsonFiles = files.filter(file => 
      path.extname(file).toLowerCase() === '.json' && file !== '.DS_Store'
    );
    
    const conversations = await Promise.all(
      jsonFiles.map(async (file) => {
        const filePath = path.join(historyDir, file);
        try {
          const content = await fs.readFile(filePath, 'utf-8');
          const conversation = JSON.parse(content);
          return {
            id: path.parse(file).name,
            name: conversation.name || 'Untitled Conversation',
            messages: conversation.messages || [],
          };
        } catch (error) {
          console.error(`Error parsing file ${file}:`, error);
          return null;
        }
      })
    );
    
    const validConversations = conversations.filter(conv => conv !== null);
    return NextResponse.json(validConversations);
  } catch (error) {
    console.error('Error reading conversations:', error);
    return NextResponse.json({ error: 'Failed to load conversations' }, { status: 500 });
  }
}