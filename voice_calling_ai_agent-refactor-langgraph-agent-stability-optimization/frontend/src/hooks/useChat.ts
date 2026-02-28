/**
 * useChat Hook
 * ============
 * 
 * Custom hook for chat functionality.
 */

import { useCallback, useState } from 'react';
import { useChat as useChatContext } from '@/store/context/ChatContext';
import { useApp } from '@/store/context';
import { sendMessageStream } from '@/services/chat';
import type { ChatMessage } from '@/types/chat';

export function useChatMessage() {
  const { sessionId } = useApp();
  const { addMessage, updateLastMessage } = useChatContext();
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

      // Add empty assistant message that will be updated with tokens
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
      };
      addMessage(assistantMessage);

      try {
        let fullResponse = '';
        
        await sendMessageStream(
          content.trim(),
          sessionId,
          (token: string) => {
            fullResponse += token;
            // Update the last message in real-time as tokens arrive
            updateLastMessage(fullResponse);
          }
        );

        return fullResponse;
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to send message';
        setError(errorMessage);
        console.error('Error sending chat message:', err);
        return null;
      } finally {
        setIsSending(false);
      }
    },
    [sessionId, addMessage, updateLastMessage]
  );

  return {
    sendChatMessage,
    isSending,
    error,
    clearError: () => setError(null),
  };
}

