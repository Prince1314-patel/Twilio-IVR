/**
 * API Type Definitions
 * ====================
 * 
 * TypeScript interfaces for API responses and error handling.
 */

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
}

