/**
 * App with Metrics Dashboard
 * ===========================
 * 
 * Enhanced App component with metrics dashboard routing.
 * 
 * To use this version:
 * 1. Rename this file to App.tsx (backup the original first)
 * 2. Or import and use this component in main.tsx
 */

import { useState } from 'react';
import { PatientAssistantShell } from "@/features/assistant/PatientAssistantShell";
import { AppProvider, ChatProvider, VoiceProvider } from "@/store/context";
import { MetricsPage } from './pages/MetricsPage';
import { BarChart3, MessageSquare } from 'lucide-react';

type Page = 'assistant' | 'metrics';

function AppWithMetrics() {
  const [currentPage, setCurrentPage] = useState<Page>('assistant');

  return (
    <div className="h-screen w-screen overflow-hidden">
      {/* Navigation Bar */}
      <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-gray-900">Healthcare AI Assistant</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage('assistant')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              currentPage === 'assistant'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span className="font-medium">Assistant</span>
          </button>
          <button
            onClick={() => setCurrentPage('metrics')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              currentPage === 'metrics'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span className="font-medium">Metrics</span>
          </button>
        </div>
      </nav>

      {/* Page Content */}
      <div className="h-[calc(100vh-60px)] overflow-auto">
        {currentPage === 'assistant' ? (
          <AppProvider>
            <ChatProvider>
              <VoiceProvider>
                <PatientAssistantShell />
              </VoiceProvider>
            </ChatProvider>
          </AppProvider>
        ) : (
          <MetricsPage />
        )}
      </div>
    </div>
  );
}

export default AppWithMetrics;
