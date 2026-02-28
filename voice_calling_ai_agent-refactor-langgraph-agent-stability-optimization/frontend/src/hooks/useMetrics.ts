/**
 * Metrics Hook
 * =============
 * 
 * React hook for fetching and managing metrics data.
 */

import { useState, useEffect, useCallback } from 'react';
import { metricsService } from '../services/metrics';
import type {
  MetricsSummary,
  MetricEvent,
  SessionMetrics,
  MetricsHealth,
  MetricsFilters
} from '../types/metrics';

export function useMetrics(timeWindowHours?: number, autoRefresh = false, refreshInterval = 30000) {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await metricsService.getSummary(timeWindowHours);
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch metrics');
      console.error('Error fetching metrics summary:', err);
    } finally {
      setLoading(false);
    }
  }, [timeWindowHours]);

  useEffect(() => {
    let mounted = true;
    
    const fetch = async () => {
      if (mounted) {
        await fetchSummary();
      }
    };

    fetch();

    if (autoRefresh) {
      const interval = setInterval(() => {
        if (mounted) {
          fetch();
        }
      }, refreshInterval);
      return () => {
        mounted = false;
        clearInterval(interval);
      };
    }

    return () => {
      mounted = false;
    };
  }, [timeWindowHours, autoRefresh, refreshInterval]);

  return {
    summary,
    loading,
    error,
    refresh: fetchSummary,
  };
}

export function useMetricEvents(filters?: MetricsFilters) {
  const [events, setEvents] = useState<MetricEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filtersString = JSON.stringify(filters);

  const fetchEvents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await metricsService.getEvents(filters);
      setEvents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch events');
      console.error('Error fetching metric events:', err);
    } finally {
      setLoading(false);
    }
  }, [filtersString]);

  useEffect(() => {
    fetchEvents();
  }, [filtersString]);

  return {
    events,
    loading,
    error,
    refresh: fetchEvents,
  };
}

export function useSessionMetrics(sessionId: string | null) {
  const [sessionMetrics, setSessionMetrics] = useState<SessionMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSessionMetrics = useCallback(async () => {
    if (!sessionId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await metricsService.getSessionMetrics(sessionId);
      setSessionMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch session metrics');
      console.error('Error fetching session metrics:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSessionMetrics();
  }, [fetchSessionMetrics]);

  return {
    sessionMetrics,
    loading,
    error,
    refresh: fetchSessionMetrics,
  };
}

export function useMetricsHealth(autoRefresh = true, refreshInterval = 60000) {
  const [health, setHealth] = useState<MetricsHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await metricsService.getHealth();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health status');
      console.error('Error fetching metrics health:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    
    const fetch = async () => {
      if (mounted) {
        await fetchHealth();
      }
    };

    fetch();

    if (autoRefresh) {
      const interval = setInterval(() => {
        if (mounted) {
          fetch();
        }
      }, refreshInterval);
      return () => {
        mounted = false;
        clearInterval(interval);
      };
    }

    return () => {
      mounted = false;
    };
  }, [autoRefresh, refreshInterval]);

  return {
    health,
    loading,
    error,
    refresh: fetchHealth,
  };
}
