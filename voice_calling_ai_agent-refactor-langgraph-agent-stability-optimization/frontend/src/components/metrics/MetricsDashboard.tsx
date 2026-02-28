/**
 * Metrics Dashboard Component
 * ============================
 * 
 * Main dashboard for operational metrics visualization.
 */

import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Shield,
  TrendingUp,
  Users,
  RefreshCw,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useMetrics, useMetricEvents, useMetricsHealth } from '../../hooks/useMetrics';
import { MetricCard } from './MetricCard';
import { BarChart } from './BarChart';
import { EventsTable } from './EventsTable';

const TIME_WINDOWS = [
  { label: '1 Hour', value: 1 },
  { label: '6 Hours', value: 6 },
  { label: '24 Hours', value: 24 },
  { label: '7 Days', value: 168 },
  { label: 'All Time', value: undefined },
];

export function MetricsDashboard() {
  const [timeWindow, setTimeWindow] = useState<number | undefined>(24);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const { summary, loading, error, refresh } = useMetrics(timeWindow, autoRefresh, 30000);
  const { events, loading: eventsLoading } = useMetricEvents({ limit: 50 });
  const { health } = useMetricsHealth(false, 60000);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 font-semibold mb-2">Error loading metrics</p>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={refresh}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  // Prepare chart data
  const guardFailuresData = Object.entries(summary.guard_failures_by_type).map(
    ([label, value]) => ({ label, value })
  );

  const escalationsData = Object.entries(summary.escalations_by_reason).map(
    ([label, value]) => ({ label, value })
  );

  const intentOverridesData = Object.entries(summary.intent_override_patterns)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  const eventsByTypeData = Object.entries(summary.events_by_type).map(
    ([label, value]) => ({ label, value })
  );

  return (
    <div className="min-h-screen bg-gray-50 p-6 pt-2">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Operational Metrics</h1>
            <p className="text-gray-600 mt-1">
              Real-time monitoring of guard failures, escalations, and system events
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Health Status */}
            {health && (
              <div
                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  health.status === 'healthy'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                <div
                  className={`w-2 h-2 rounded-full ${
                    health.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="font-medium text-sm">
                  {health.status === 'healthy' ? 'System Healthy' : 'System Issues'}
                </span>
              </div>
            )}

            {/* Auto Refresh Toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                autoRefresh
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-200 text-gray-700'
              }`}
            >
              <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
              <span className="text-sm font-medium">
                {autoRefresh ? 'Auto-refresh On' : 'Auto-refresh Off'}
              </span>
            </button>

            {/* Manual Refresh */}
            <button
              onClick={refresh}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>
        </div>

        {/* Time Window Selector */}
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600 mr-2">Time Window:</span>
          {TIME_WINDOWS.map((window) => (
            <button
              key={window.label}
              onClick={() => setTimeWindow(window.value)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                timeWindow === window.value
                  ? 'bg-blue-500 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {window.label}
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Total Events"
          value={summary.total_events.toLocaleString()}
          icon={Activity}
          subtitle={`${summary.events_last_hour} in last hour`}
          color="blue"
        />
        <MetricCard
          title="Guard Failures"
          value={summary.guard_failures_total}
          icon={Shield}
          subtitle={`${Object.keys(summary.guard_failures_by_type).length} types`}
          color="red"
        />
        <MetricCard
          title="Escalations"
          value={summary.escalations_total}
          icon={AlertTriangle}
          subtitle={`${Object.keys(summary.escalations_by_reason).length} reasons`}
          color="yellow"
        />
        <MetricCard
          title="Intent Overrides"
          value={summary.intent_overrides_total}
          icon={TrendingUp}
          subtitle={`${Object.keys(summary.intent_override_patterns).length} patterns`}
          color="purple"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <MetricCard
          title="Safety Conflicts"
          value={summary.safety_conflicts_total}
          icon={AlertCircle}
          color="red"
        />
        <MetricCard
          title="Validation Failures"
          value={summary.validation_failures_total}
          icon={AlertCircle}
          color="yellow"
        />
        <MetricCard
          title="Intent Mismatches"
          value={summary.intent_mismatches_total}
          icon={Users}
          color="blue"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <BarChart
          title="Guard Failures by Type"
          data={guardFailuresData}
          height={300}
        />
        <BarChart
          title="Escalations by Reason"
          data={escalationsData}
          height={300}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <BarChart
          title="Top Intent Override Patterns"
          data={intentOverridesData}
          height={300}
        />
        <BarChart
          title="Events by Type"
          data={eventsByTypeData}
          height={300}
        />
      </div>

      {/* Recent Events Table */}
      <EventsTable
        title="Recent Events"
        events={events}
        maxHeight="600px"
      />
    </div>
  );
}
