/**
 * useChat Hook
 * ============
 * 
 * Custom hook for chat functionality.
 */

import { useCallback, useState } from 'react';
import { useChat as useChatContext } from '@/store/context/ChatContext';
import { useApp } from '@/store/context';
import { sendMessage } from '@/services/chat';
import type { ChatMessage } from '@/types/chat';

export function useChatMessage() {
  const { sessionId } = useApp();
  const { addMessage } = useChatContext();
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendChatMessage = useCallback(
    async (content: string): Promise<string | null> => {
      if (!content.trim()) return null;

      setIsSending(true);
      setError(null);

      // Add user message immediately
      const userMessage: ChatMessage = {
        role: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
      };
      addMessage(userMessage);

      try {
        const response = await sendMessage(content.trim(), sessionId);
        
        // Add assistant response
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.content,
          timestamp: response.timestamp,
        };
        addMessage(assistantMessage);

        return response.content;
      } catch (err: any) {
        const errorMessage = err.detail || 'Failed to send message';
        setError(errorMessage);
        console.error('Error sending chat message:', err);
        return null;
      } finally {
        setIsSending(false);
      }
    },
    [sessionId, addMessage]
  );

  return {
    sendChatMessage,
    isSending,
    error,
    clearError: () => setError(null),
  };
}

