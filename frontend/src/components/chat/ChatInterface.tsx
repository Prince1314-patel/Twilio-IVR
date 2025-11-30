/**
 * Chat Interface Component
 * ========================
 * 
 * Main chat interface component with message list and input.
 */

import React, { useEffect, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { useChat } from '@/store/context';
import { useChatMessage } from '@/hooks/useChat';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

export function ChatInterface() {
  const { messages, isLoading } = useChat();
  const { sendChatMessage, isSending, error, clearError } = useChatMessage();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    await sendChatMessage(content);
    clearError();
  };

  return (
    <Card className="flex flex-col h-full max-h-[calc(100vh-200px)]">
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="space-y-2">
          {messages.length === 0 && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-center text-muted-foreground">
              <p className="text-lg font-medium mb-2">Welcome to Healthcare AI Assistant</p>
              <p className="text-sm">
                Start a conversation by typing a message below.
                <br />
                You can schedule appointments, check availability, and more.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}

          {isSending && (
            <div className="flex gap-3 mb-4">
              <div className="flex flex-col gap-2">
                <div className="bg-muted rounded-tl-sm rounded-2xl px-4 py-2">
                  <Skeleton className="h-4 w-32" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {error && (
        <Alert variant="destructive" className="m-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <ChatInput onSendMessage={handleSendMessage} isLoading={isSending} disabled={isLoading} />
    </Card>
  );
}

