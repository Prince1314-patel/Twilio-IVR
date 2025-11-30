/**
 * Chat API Service
 * ================
 * 
 * API service methods for chat functionality.
 */

import api from './api';
import type { ChatRequest, ChatResponse, ConversationHistory, ActiveSessions } from '@/types/chat';

/**
 * Send a chat message to the AI assistant.
 */
export async function sendMessage(content: string, sessionId?: string): Promise<ChatResponse> {
  const payload: ChatRequest = {
    content,
    session_id: sessionId,
    timestamp: new Date().toISOString(),
  };

  const response = await api.post<ChatResponse>('/api/chat/message', payload);
  return response.data;
}

/**
 * Get conversation history for a session.
 */
export async function getHistory(sessionId: string): Promise<ConversationHistory> {
  const response = await api.get<ConversationHistory>(`/api/chat/history/${sessionId}`);
  return response.data;
}

/**
 * Clear conversation history for a session.
 */
export async function clearHistory(sessionId: string): Promise<void> {
  await api.delete(`/api/chat/history/${sessionId}`);
}

/**
 * Create a new chat session.
 */
export async function createSession(): Promise<{ session_id: string; message: string }> {
  const response = await api.post<{ session_id: string; message: string }>('/api/chat/new-session');
  return response.data;
}

/**
 * Get list of active sessions.
 */
export async function getActiveSessions(): Promise<ActiveSessions> {
  const response = await api.get<ActiveSessions>('/api/chat/sessions');
  return response.data;
}

