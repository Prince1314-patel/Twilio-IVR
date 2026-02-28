/**
 * Voice Call API Service
 * ======================
 * 
 * API service methods for voice call functionality.
 */

import api from './api';
import type { CallRequest, CallResponse, CallStatus, ActiveCalls } from '@/types/voice';

/**
 * Initiate a voice call to the specified phone number.
 */
export async function initiateCall(phoneNumber: string, message?: string): Promise<CallResponse> {
  const payload: CallRequest = {
    phone_number: phoneNumber,
    message: message || 'Healthcare AI Assistant calling',
  };

  const response = await api.post<CallResponse>('/api/voice/initiate-call', payload);
  return response.data;
}

/**
 * Get the status of a voice call.
 */
export async function getCallStatus(callSid: string): Promise<CallStatus> {
  const response = await api.get<CallStatus>(`/api/voice/call-status/${callSid}`);
  return response.data;
}

/**
 * Get list of active calls.
 */
export async function getActiveCalls(): Promise<ActiveCalls> {
  const response = await api.get<ActiveCalls>('/api/voice/active-calls');
  return response.data;
}

