/**
 * Chat Context
 * ============
 * 
 * Context for managing chat messages and conversation history.
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import type { ChatMessage } from '@/types/chat';
import { getHistory, clearHistory as clearHistoryApi } from '@/services/chat';
import { useApp } from './AppContext';

interface ChatContextType {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => Promise<void>;
  loadHistory: () => Promise<void>;
  clearError: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const { sessionId } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load conversation history when session changes
  useEffect(() => {
    if (sessionId) {
      loadHistory();
    }
  }, [sessionId]);

  const loadHistory = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);
    try {
      const history = await getHistory(sessionId);
      setMessages(history.messages);
    } catch (err: any) {
      setError(err.detail || 'Failed to load conversation history');
      console.error('Error loading history:', err);
      // Don't clear messages on error, keep existing ones
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const clearMessages = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);
    try {
      await clearHistoryApi(sessionId);
      setMessages([]);
    } catch (err: any) {
      setError(err.detail || 'Failed to clear conversation history');
      console.error('Error clearing history:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        messages,
        isLoading,
        error,
        addMessage,
        clearMessages,
        loadHistory,
        clearError,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}

