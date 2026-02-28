/**
 * App Context
 * ===========
 * 
 * Main application context for session management and global state.
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { createSession } from '@/services/chat';

interface AppContextType {
  sessionId: string;
  isLoading: boolean;
  error: string | null;
  createNewSession: () => Promise<void>;
  clearError: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string>(() => {
    // Try to get from localStorage, otherwise generate new
    const stored = localStorage.getItem('sessionId');
    return stored || uuidv4();
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Save session ID to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('sessionId', sessionId);
  }, [sessionId]);

  const createNewSession = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await createSession();
      setSessionId(response.session_id);
    } catch (err: any) {
      setError(err.detail || 'Failed to create new session');
      console.error('Error creating session:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  return (
    <AppContext.Provider
      value={{
        sessionId,
        isLoading,
        error,
        createNewSession,
        clearError,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
