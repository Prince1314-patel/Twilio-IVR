/**
 * Voice Call Type Definitions
 * ===========================
 * 
 * TypeScript interfaces for voice call-related data structures.
 */

export interface CallRequest {
  phone_number: string;
  message?: string;
}

export interface CallResponse {
  call_sid: string;
  status: string;
  message: string;
}

export interface CallStatus {
  call_sid: string;
  status: string;
  direction: string;
  from: string;
  to: string;
  start_time: string | null;
  end_time: string | null;
  duration: string | null;
}

export interface ActiveCalls {
  active_calls: number;
  call_sessions: string[];
}

