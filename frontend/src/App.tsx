/**
 * Main Application Component
 * ==========================
 * 
 * Root application component with layout and context providers.
 */

import React from 'react';
import { AppProvider, ChatProvider, VoiceProvider } from '@/store/context';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';
import { Sidebar } from '@/components/sidebar/Sidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
// Toast notifications will be added if needed
// import { Toaster } from '@/components/ui/sonner';

function App() {
  return (
    <AppProvider>
      <ChatProvider>
        <VoiceProvider>
          <div className="min-h-screen flex flex-col bg-gradient-to-br from-background to-muted/20">
            <Header />
            
            <main className="flex-1 container mx-auto px-4 py-6">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full">
                {/* Sidebar - Hidden on mobile, visible on desktop */}
                <aside className="hidden lg:block lg:col-span-1">
                  <div className="sticky top-6">
                    <Sidebar />
                  </div>
                </aside>

                {/* Main Chat Area */}
                <div className="lg:col-span-3">
                  <ChatInterface />
                </div>
              </div>
            </main>

            <Footer />
          </div>
        </VoiceProvider>
      </ChatProvider>
    </AppProvider>
  );
}

export default App;

