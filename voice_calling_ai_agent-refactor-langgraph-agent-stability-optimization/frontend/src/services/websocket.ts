/**
 * WebSocket Service
 * =================
 * 
 * WebSocket client for real-time communication (optional enhancement).
 */

import { WEBSOCKET_URL } from '@/utils/constants';

export type WebSocketMessage = {
  type: string;
  content?: string;
  timestamp?: string;
};

export type WebSocketCallbacks = {
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
  onOpen?: () => void;
};

class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private callbacks: WebSocketCallbacks = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  connect(sessionId: string, callbacks: WebSocketCallbacks = {}): void {
    this.sessionId = sessionId;
    this.callbacks = callbacks;
    this.reconnectAttempts = 0;
    this.doConnect();
  }

  private doConnect(): void {
    if (!this.sessionId) return;

    try {
      const url = `${WEBSOCKET_URL}/${this.sessionId}`;
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.callbacks.onOpen?.();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.callbacks.onMessage?.(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        this.callbacks.onError?.(error);
      };

      this.ws.onclose = () => {
        this.callbacks.onClose?.();
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.callbacks.onError?.(error as Event);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    setTimeout(() => {
      if (this.sessionId) {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.doConnect();
      }
    }, this.reconnectDelay);
  }

  send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.callbacks = {};
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const websocketClient = new WebSocketClient();

