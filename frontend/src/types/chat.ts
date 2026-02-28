/**
 * Chat Type Definitions
 * =====================
 * 
 * TypeScript interfaces for chat-related data structures.
 */

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  content: string;
  session_id?: string;
  timestamp?: string;
}

export interface ChatResponse {
  content: string;
  session_id: string;
  timestamp: string;
  message_type: string;
}

export interface ConversationHistory {
  session_id: string;
  messages: ChatMessage[];
  total_messages: number;
}

export interface SessionInfo {
  session_id: string;
  message_count: number;
  last_activity: string | null;
}

export interface ActiveSessions {
  active_sessions: number;
  sessions: SessionInfo[];
}

