/**
 * useVoiceCall Hook
 * =================
 * 
 * Custom hook for voice call functionality.
 */

import { useCallback, useState } from 'react';
import { useVoice } from '@/store/context/VoiceContext';
import { initiateCall } from '@/services/voice';
import { validatePhoneNumber } from '@/utils/helpers';

export function useVoiceCallInitiate() {
  const { setCallSid, startPolling } = useVoice();
  const [isInitiating, setIsInitiating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initiateVoiceCall = useCallback(
    async (phoneNumber: string, message?: string): Promise<boolean> => {
      // Validate phone number
      if (!validatePhoneNumber(phoneNumber)) {
        setError('Invalid phone number format. Please use E.164 format (e.g., +1234567890)');
        return false;
      }

      setIsInitiating(true);
      setError(null);

      try {
        const response = await initiateCall(phoneNumber, message);
        setCallSid(response.call_sid);
        startPolling();
        return true;
      } catch (err: any) {
        const errorMessage = err.detail || 'Failed to initiate call';
        setError(errorMessage);
        console.error('Error initiating call:', err);
        return false;
      } finally {
        setIsInitiating(false);
      }
    },
    [setCallSid, startPolling]
  );

  return {
    initiateVoiceCall,
    isInitiating,
    error,
    clearError: () => setError(null),
  };
}

