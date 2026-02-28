/**
 * Metrics Dashboard Examples
 * ==========================
 * 
 * Example usage of metrics components and hooks.
 */

import React from 'react';
import { useMetrics, useMetricEvents } from '../hooks/useMetrics';
import { MetricCard, BarChart, EventsTable } from '../components/metrics';
import { Activity, Shield, AlertTriangle } from 'lucide-react';

/**
 * Example 1: Simple Metrics Display
 */
export function SimpleMetricsExample() {
  const { summary, loading, error } = useMetrics(24); // Last 24 hours

  if (loading) return <div>Loading metrics...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!summary) return null;

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Simple Metrics Example</h2>
      
      <div className="grid grid-cols-3 gap-4">
        <MetricCard
          title="Total Events"
          value={summary.total_events}
          icon={Activity}
          color="blue"
        />
        <MetricCard
          title="Guard Failures"
          value={summary.guard_failures_total}
          icon={Shield}
          color="red"
        />
        <MetricCard
          title="Escalations"
          value={summary.escalations_total}
          icon={AlertTriangle}
          color="yellow"
        />
      </div>
    </div>
  );
}

/**
 * Example 2: Guard Failures Chart
 */
export function GuardFailuresChartExample() {
  const { summary, loading } = useMetrics(24);

  if (loading || !summary) return <div>Loading...</div>;

  const chartData = Object.entries(summary.guard_failures_by_type).map(
    ([label, value]) => ({ label, value })
  );

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Guard Failures Chart</h2>
      <BarChart
        title="Guard Failures by Type (Last 24 Hours)"
        data={chartData}
        height={300}
      />
    </div>
  );
}

/**
 * Example 3: Recent Events Table
 */
export function RecentEventsExample() {
  const { events, loading } = useMetricEvents({ limit: 20 });

  if (loading) return <div>Loading events...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Recent Events</h2>
      <EventsTable events={events} maxHeight="400px" />
    </div>
  );
}

/**
 * Example 4: Filtered Events (Guard Failures Only)
 */
export function FilteredEventsExample() {
  const { events, loading } = useMetricEvents({
    metricType: 'guard_failure',
    limit: 10
  });

  if (loading) return <div>Loading guard failures...</div>;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">Recent Guard Failures</h2>
      <EventsTable
        title="Guard Failure Events"
        events={events}
        maxHeight="300px"
      />
    </div>
  );
}

/**
 * Example 5: Custom Metrics Display
 */
export function CustomMetricsExample() {
  const { summary, loading, refresh } = useMetrics(1); // Last hour

  if (loading || !summary) return <div>Loading...</div>;

  const escalationRate = summary.total_events > 0
    ? (summary.escalations_total / summary.total_events) * 100
    : 0;

  const guardFailureRate = summary.total_events > 0
    ? (summary.guard_failures_total / summary.total_events) * 100
    : 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Custom Metrics (Last Hour)</h2>
        <button
          onClick={refresh}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Escalation Rate
          </h3>
          <p className="text-3xl font-bold text-orange-600">
            {escalationRate.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {summary.escalations_total} of {summary.total_events} events
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg border">
          <h3 className="text-sm font-medium text-gray-600 mb-2">
            Guard Failure Rate
          </h3>
          <p className="text-3xl font-bold text-red-600">
            {guardFailureRate.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-500 mt-1">
            {summary.guard_failures_total} of {summary.total_events} events
          </p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4">Event Distribution</h3>
        <div className="space-y-2">
          {Object.entries(summary.events_by_type).map(([type, count]) => (
            <div key={type} className="flex items-center justify-between">
              <span className="text-sm text-gray-600 capitalize">
                {type.replace(/_/g, ' ')}
              </span>
              <span className="text-sm font-semibold text-gray-900">
                {count}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Example 6: All Examples Combined
 */
export function AllMetricsExamples() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 space-y-8">
        <h1 className="text-4xl font-bold text-center mb-8">
          Metrics Dashboard Examples
        </h1>
        
        <SimpleMetricsExample />
        <GuardFailuresChartExample />
        <CustomMetricsExample />
        <RecentEventsExample />
        <FilteredEventsExample />
      </div>
    </div>
  );
}
