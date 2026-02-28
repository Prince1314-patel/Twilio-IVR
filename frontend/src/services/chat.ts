/**
 * Chat API Service
 * ================
 * 
 * API service methods for chat functionality.
 */

import api from './api';
import { API_BASE_URL } from '@/utils/constants';
import type { ChatRequest, ChatResponse, ConversationHistory, ActiveSessions } from '@/types/chat';

/**
 * Send a chat message to the AI assistant and stream the response.
 * Calls onToken for each token received.
 */
export async function sendMessageStream(
  content: string,
  sessionId: string | undefined,
  onToken: (token: string) => void
): Promise<string> {
  const payload: ChatRequest = {
    content,
    session_id: sessionId,
    timestamp: new Date().toISOString(),
  };

  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  let fullResponse = '';
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    
    // Process all complete lines, keep incomplete line in buffer
    for (let i = 0; i < lines.length - 1; i++) {
      const line = lines[i].trim();
      if (line) {
        try {
          const json = JSON.parse(line);
          if (json.token) {
            fullResponse += json.token;
            onToken(json.token);
          }
        } catch (e) {
          console.error('Error parsing token:', e);
        }
      }
    }
    buffer = lines[lines.length - 1];
  }

  // Process remaining buffer
  if (buffer.trim()) {
    try {
      const json = JSON.parse(buffer);
      if (json.token) {
        fullResponse += json.token;
        onToken(json.token);
      }
    } catch (e) {
      console.error('Error parsing final token:', e);
    }
  }

  return fullResponse;
}

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

export interface UserDetails {
  id: number;
  full_name: string | null;
  mobile_number: string;
  created_at: string | null;
}

export async function lookupUser(phoneNumber: string): Promise<UserDetails> {
  const response = await api.post<UserDetails>('/api/chat/user-lookup', { phone_number: phoneNumber });
  return response.data;
}

/**
 * Identify user and link to session.
 */
export async function identifyUser(phoneNumber: string, sessionId: string): Promise<{ message: string; user: UserDetails }> {
  const response = await api.post<{ message: string; user: UserDetails }>('/api/chat/identify', {
    phone_number: phoneNumber,
    session_id: sessionId
  });
  return response.data;
}



