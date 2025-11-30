/**
 * Voice Context
 * =============
 * 
 * Context for managing voice call state and status.
 */

import React, { createContext, useContext, useState, useEffect, useRef, ReactNode, useCallback } from 'react';
import type { CallStatus } from '@/types/voice';
import { getCallStatus } from '@/services/voice';
import { CALL_STATUS_POLL_INTERVAL } from '@/utils/constants';

interface VoiceContextType {
  callSid: string | null;
  callStatus: CallStatus | null;
  isCallActive: boolean;
  isPolling: boolean;
  setCallSid: (sid: string | null) => void;
  startPolling: () => void;
  stopPolling: () => void;
  clearCall: () => void;
}

const VoiceContext = createContext<VoiceContextType | undefined>(undefined);

export function VoiceProvider({ children }: { children: ReactNode }) {
  const [callSid, setCallSid] = useState<string | null>(() => {
    // Try to get from sessionStorage
    return sessionStorage.getItem('callSid');
  });
  const [callStatus, setCallStatus] = useState<CallStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingIntervalRef = useRef<number | null>(null);

  const isCallActive = callSid !== null;

  // Save call SID to sessionStorage when it changes
  useEffect(() => {
    if (callSid) {
      sessionStorage.setItem('callSid', callSid);
    } else {
      sessionStorage.removeItem('callSid');
    }
  }, [callSid]);

  const pollCallStatus = useCallback(async () => {
    if (!callSid || !isPolling) return;

    try {
      const status = await getCallStatus(callSid);
      setCallStatus(status);

      // Stop polling if call is completed or failed
      if (['completed', 'failed', 'canceled', 'busy', 'no-answer'].includes(status.status)) {
        stopPolling();
      }
    } catch (error) {
      console.error('Error polling call status:', error);
      // Don't stop polling on error, might be temporary
    }
  }, [callSid, isPolling]);

  const startPolling = useCallback(() => {
    if (pollingIntervalRef.current) return; // Already polling

    setIsPolling(true);
    pollCallStatus(); // Poll immediately
    pollingIntervalRef.current = window.setInterval(() => {
      pollCallStatus();
    }, CALL_STATUS_POLL_INTERVAL);
  }, [pollCallStatus]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const clearCall = useCallback(() => {
    stopPolling();
    setCallSid(null);
    setCallStatus(null);
    sessionStorage.removeItem('callSid');
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Auto-start polling when call SID is set
  useEffect(() => {
    if (callSid && !isPolling) {
      startPolling();
    }
  }, [callSid, isPolling, startPolling]);

  return (
    <VoiceContext.Provider
      value={{
        callSid,
        callStatus,
        isCallActive,
        isPolling,
        setCallSid,
        startPolling,
        stopPolling,
        clearCall,
      }}
    >
      {children}
    </VoiceContext.Provider>
  );
}

export function useVoice() {
  const context = useContext(VoiceContext);
  if (context === undefined) {
    throw new Error('useVoice must be used within a VoiceProvider');
  }
  return context;
}

