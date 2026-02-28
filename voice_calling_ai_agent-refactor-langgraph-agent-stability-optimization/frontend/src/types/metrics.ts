/**
 * Metrics Type Definitions
 * =========================
 * 
 * TypeScript types for operational metrics system.
 */

export interface MetricEvent {
  metric_type: string;
  timestamp: number;
  datetime: string;
  user_id: number | null;
  session_id: string | null;
  details: Record<string, any>;
}

export interface MetricsSummary {
  total_events: number;
  events_by_type: Record<string, number>;
  events_last_hour: number;
  events_last_24h: number;
  guard_failures_total: number;
  guard_failures_by_type: Record<string, number>;
  escalations_total: number;
  escalations_by_reason: Record<string, number>;
  intent_mismatches_total: number;
  intent_overrides_total: number;
  intent_override_patterns: Record<string, number>;
  safety_conflicts_total: number;
  validation_failures_total: number;
  start_time: number | null;
  end_time: number | null;
}

export interface SessionMetrics {
  session_id: string;
  total_events: number;
  events_by_type: Record<string, number>;
  events: MetricEvent[];
}

export interface MetricsHealth {
  status: 'healthy' | 'unhealthy';
  total_events: number;
  events_last_hour: number;
  events_last_24h: number;
  error?: string;
}

export type MetricType =
  | 'guard_failure'
  | 'escalation'
  | 'intent_mismatch'
  | 'intent_override'
  | 'safety_conflict'
  | 'validation_failure'
  | 'name_gate_block'
  | 'tool_execution_error';

export interface MetricsFilters {
  timeWindowHours?: number;
  metricType?: MetricType;
  sessionId?: string;
  limit?: number;
}
