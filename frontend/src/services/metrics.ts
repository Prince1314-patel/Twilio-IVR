/**
 * Metrics Service
 * ================
 * 
 * API service for operational metrics endpoints.
 */

import axios from 'axios';
import type {
  MetricsSummary,
  MetricEvent,
  SessionMetrics,
  MetricsHealth,
  MetricsFilters,
  MetricType
} from '../types/metrics';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const metricsApi = axios.create({
  baseURL: `${API_BASE_URL}/api/metrics`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const metricsService = {
  /**
   * Get aggregated metrics summary
   */
  async getSummary(timeWindowHours?: number): Promise<MetricsSummary> {
    const params = timeWindowHours ? { time_window_hours: timeWindowHours } : {};
    const response = await metricsApi.get<MetricsSummary>('/summary', { params });
    return response.data;
  },

  /**
   * Get recent metric events with optional filtering
   */
  async getEvents(filters?: MetricsFilters): Promise<MetricEvent[]> {
    const params: Record<string, any> = {};
    
    if (filters?.metricType) params.metric_type = filters.metricType;
    if (filters?.sessionId) params.session_id = filters.sessionId;
    if (filters?.limit) params.limit = filters.limit;
    
    const response = await metricsApi.get<MetricEvent[]>('/events', { params });
    return response.data;
  },

  /**
   * Get metrics for a specific session
   */
  async getSessionMetrics(sessionId: string): Promise<SessionMetrics> {
    const response = await metricsApi.get<SessionMetrics>(`/session/${sessionId}`);
    return response.data;
  },

  /**
   * Get guard failure counts by type
   */
  async getGuardFailures(timeWindowHours?: number): Promise<Record<string, number>> {
    const params = timeWindowHours ? { time_window_hours: timeWindowHours } : {};
    const response = await metricsApi.get<Record<string, number>>('/guard-failures', { params });
    return response.data;
  },

  /**
   * Get escalation counts by reason
   */
  async getEscalations(timeWindowHours?: number): Promise<Record<string, number>> {
    const params = timeWindowHours ? { time_window_hours: timeWindowHours } : {};
    const response = await metricsApi.get<Record<string, number>>('/escalations', { params });
    return response.data;
  },

  /**
   * Get intent override patterns
   */
  async getIntentOverrides(timeWindowHours?: number): Promise<Record<string, number>> {
    const params = timeWindowHours ? { time_window_hours: timeWindowHours } : {};
    const response = await metricsApi.get<Record<string, number>>('/intent-overrides', { params });
    return response.data;
  },

  /**
   * Trigger manual cleanup of old metrics
   */
  async cleanup(): Promise<{ status: string; events_removed: number }> {
    const response = await metricsApi.post<{ status: string; events_removed: number }>('/cleanup');
    return response.data;
  },

  /**
   * Check metrics system health
   */
  async getHealth(): Promise<MetricsHealth> {
    const response = await metricsApi.get<MetricsHealth>('/health');
    return response.data;
  },
};
