/**
 * useWebSocket Hook
 * =================
 * 
 * Custom hook for WebSocket connection (optional enhancement).
 */

import { useEffect, useCallback, useRef } from 'react';
import { websocketClient, type WebSocketCallbacks } from '@/services/websocket';
import { useApp } from '@/store/context/AppContext';

export function useWebSocketConnection(callbacks: WebSocketCallbacks = {}) {
  const { sessionId } = useApp();
  const callbacksRef = useRef(callbacks);

  // Update callbacks ref when they change
  useEffect(() => {
    callbacksRef.current = callbacks;
  }, [callbacks]);

  const send = useCallback((message: { type: string; content?: string; timestamp?: string }) => {
    websocketClient.send(message);
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const wrappedCallbacks: WebSocketCallbacks = {
      onMessage: (msg) => callbacksRef.current.onMessage?.(msg),
      onError: (err) => callbacksRef.current.onError?.(err),
      onClose: () => callbacksRef.current.onClose?.(),
      onOpen: () => callbacksRef.current.onOpen?.(),
    };

    websocketClient.connect(sessionId, wrappedCallbacks);

    return () => {
      websocketClient.disconnect();
    };
  }, [sessionId]);

  return {
    send,
    isConnected: websocketClient.isConnected(),
  };
}

