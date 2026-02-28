/**
 * useSession Hook
 * ===============
 * 
 * Custom hook for session management.
 */

import { useCallback } from 'react';
import { useApp } from '@/store/context/AppContext';
import { useChat } from '@/store/context/ChatContext';

export function useSessionManagement() {
  const { sessionId, createNewSession } = useApp();
  const { clearMessages, loadHistory } = useChat();

  const startNewSession = useCallback(async () => {
    await createNewSession();
    await clearMessages();
  }, [createNewSession, clearMessages]);

  const refreshSession = useCallback(async () => {
    await loadHistory();
  }, [loadHistory]);

  return {
    sessionId,
    startNewSession,
    refreshSession,
  };
}

