/**
 * Metrics Page
 * ============
 * 
 * Standalone page for the operational metrics dashboard.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { MetricsDashboard } from '../components/metrics';

export function MetricsPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Back Button */}
      <div className="bg-white border-b border-gray-200 px-6 py-3">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="font-medium">Back to Assistant</span>
        </button>
      </div>
      
      {/* Dashboard */}
      <MetricsDashboard />
    </div>
  );
}
