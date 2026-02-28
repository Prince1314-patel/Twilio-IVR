/**
 * Events Table Component
 * ======================
 * 
 * Displays recent metric events in a table format.
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import type { MetricEvent } from '../../types/metrics';

interface EventsTableProps {
  events: MetricEvent[];
  title?: string;
  maxHeight?: string;
}

const metricTypeColors: Record<string, string> = {
  guard_failure: 'bg-red-100 text-red-800',
  escalation: 'bg-orange-100 text-orange-800',
  intent_mismatch: 'bg-yellow-100 text-yellow-800',
  intent_override: 'bg-blue-100 text-blue-800',
  safety_conflict: 'bg-red-100 text-red-800',
  validation_failure: 'bg-yellow-100 text-yellow-800',
  name_gate_block: 'bg-purple-100 text-purple-800',
  tool_execution_error: 'bg-red-100 text-red-800',
};

const metricTypeLabels: Record<string, string> = {
  guard_failure: 'Guard Failure',
  escalation: 'Escalation',
  intent_mismatch: 'Intent Mismatch',
  intent_override: 'Intent Override',
  safety_conflict: 'Safety Conflict',
  validation_failure: 'Validation Failure',
  name_gate_block: 'Name Gate Block',
  tool_execution_error: 'Tool Error',
};

export function EventsTable({ events, title, maxHeight = '500px' }: EventsTableProps) {
  if (events.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
        <div className="flex items-center justify-center h-32 text-gray-400">
          No events to display
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {title && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold">{title}</h3>
        </div>
      )}
      <div className="overflow-auto" style={{ maxHeight }}>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Details
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {events.map((event, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${
                      metricTypeColors[event.metric_type] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {metricTypeLabels[event.metric_type] || event.metric_type}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDistanceToNow(new Date(event.datetime), { addSuffix: true })}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                  {event.session_id ? (
                    <span className="truncate max-w-[100px] inline-block">
                      {event.session_id.slice(0, 8)}...
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  <div className="max-w-md">
                    {Object.entries(event.details).map(([key, value]) => (
                      <div key={key} className="text-xs">
                        <span className="font-medium text-gray-600">{key}:</span>{' '}
                        <span className="text-gray-800">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
