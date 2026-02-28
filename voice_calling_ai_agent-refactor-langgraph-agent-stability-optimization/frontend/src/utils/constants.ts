/**
 * Application Constants
 * =====================
 * 
 * Centralized constants for the Healthcare AI Assistant frontend.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000/ws';

export const APP_NAME = 'Healthcare AI Assistant';
export const APP_VERSION = '2.0.0';

export const CALL_STATUS_POLL_INTERVAL = 5000; // 5 seconds
export const WEBSOCKET_RECONNECT_DELAY = 3000; // 3 seconds

export const PHONE_NUMBER_REGEX = /^\+[1-9]\d{1,14}$/;

export const CHAT_MESSAGE_MAX_LENGTH = 2000;

