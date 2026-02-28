/**
 * Mock Metrics Data
 * =================
 * 
 * Generate mock data for testing the metrics dashboard without a backend.
 * Useful for development and UI testing.
 */

import type { MetricsSummary, MetricEvent } from '../types/metrics';

/**
 * Generate mock metrics summary
 */
export function generateMockSummary(): MetricsSummary {
  return {
    total_events: 1247,
    events_by_type: {
      guard_failure: 156,
      escalation: 23,
      intent_mismatch: 89,
      intent_override: 234,
      safety_conflict: 45,
      validation_failure: 67,
      name_gate_block: 12,
      tool_execution_error: 34,
    },
    events_last_hour: 42,
    events_last_24h: 856,
    guard_failures_total: 156,
    guard_failures_by_type: {
      appointment_id_verification: 67,
      confirmation_required: 45,
      hallucination_guard: 23,
      slot_completeness: 21,
    },
    escalations_total: 23,
    escalations_by_reason: {
      safety_conflicts: 12,
      validation_failures: 8,
      name_gate_max_attempts: 3,
    },
    intent_mismatches_total: 89,
    intent_overrides_total: 234,
    intent_override_patterns: {
      'booking→cancellation': 89,
      'cancellation→rescheduling': 67,
      'booking→rescheduling': 45,
      'inquiry→booking': 23,
      'rescheduling→cancellation': 10,
    },
    safety_conflicts_total: 45,
    validation_failures_total: 67,
    start_time: Date.now() / 1000 - 86400, // 24 hours ago
    end_time: Date.now() / 1000,
  };
}

/**
 * Generate mock metric events
 */
export function generateMockEvents(count: number = 20): MetricEvent[] {
  const eventTypes = [
    'guard_failure',
    'escalation',
    'intent_mismatch',
    'intent_override',
    'safety_conflict',
    'validation_failure',
  ];

  const guardTypes = [
    'appointment_id_verification',
    'confirmation_required',
    'hallucination_guard',
    'slot_completeness',
  ];

  const escalationReasons = [
    'safety_conflicts',
    'validation_failures',
    'name_gate_max_attempts',
  ];

  const intents = ['booking', 'cancellation', 'rescheduling', 'inquiry'];

  const events: MetricEvent[] = [];

  for (let i = 0; i < count; i++) {
    const timestamp = Date.now() / 1000 - Math.random() * 86400; // Random time in last 24h
    const metricType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    
    let details: Record<string, any> = {};

    switch (metricType) {
      case 'guard_failure':
        details = {
          guard_type: guardTypes[Math.floor(Math.random() * guardTypes.length)],
          reason: 'Precondition not met',
        };
        break;
      
      case 'escalation':
        details = {
          reason: escalationReasons[Math.floor(Math.random() * escalationReasons.length)],
          safety_conflict_count: Math.floor(Math.random() * 3) + 1,
        };
        break;
      
      case 'intent_mismatch':
        const expected = intents[Math.floor(Math.random() * intents.length)];
        let actual = intents[Math.floor(Math.random() * intents.length)];
        while (actual === expected) {
          actual = intents[Math.floor(Math.random() * intents.length)];
        }
        details = {
          expected_intent: expected,
          actual_intent: actual,
          confidence: 0.5 + Math.random() * 0.4,
        };
        break;
      
      case 'intent_override':
        const from = intents[Math.floor(Math.random() * intents.length)];
        let to = intents[Math.floor(Math.random() * intents.length)];
        while (to === from) {
          to = intents[Math.floor(Math.random() * intents.length)];
        }
        details = {
          from_intent: from,
          to_intent: to,
          confidence: 0.7 + Math.random() * 0.3,
          pattern: `${from}→${to}`,
        };
        break;
      
      case 'safety_conflict':
        details = {
          conflict_type: 'unverified_appointment_id',
          appointment_id: `apt_${Math.random().toString(36).substr(2, 9)}`,
        };
        break;
      
      case 'validation_failure':
        details = {
          validation_type: 'missing_required_slots',
          missing_slots: ['date', 'time'],
        };
        break;
    }

    events.push({
      metric_type: metricType,
      timestamp,
      datetime: new Date(timestamp * 1000).toISOString(),
      user_id: Math.floor(Math.random() * 1000) + 1,
      session_id: `session_${Math.random().toString(36).substr(2, 9)}`,
      details,
    });
  }

  // Sort by timestamp (most recent first)
  return events.sort((a, b) => b.timestamp - a.timestamp);
}

/**
 * Mock metrics service for testing
 */
export const mockMetricsService = {
  getSummary: async () => {
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate network delay
    return generateMockSummary();
  },

  getEvents: async (filters?: any) => {
    await new Promise(resolve => setTimeout(resolve, 300));
    const count = filters?.limit || 20;
    return generateMockEvents(count);
  },

  getHealth: async () => {
    await new Promise(resolve => setTimeout(resolve, 100));
    return {
      status: 'healthy' as const,
      total_events: 1247,
      events_last_hour: 42,
      events_last_24h: 856,
    };
  },
};

/**
 * Usage example:
 * 
 * // In your component or hook, replace the real service with mock:
 * import { mockMetricsService } from '@/utils/mockMetricsData';
 * 
 * const summary = await mockMetricsService.getSummary();
 * const events = await mockMetricsService.getEvents({ limit: 50 });
 */
