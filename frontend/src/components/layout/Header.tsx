/**
 * Header Component
 * ================
 * 
 * Main application header with title and voice call panel.
 */

import React from 'react';
import { VoiceCallPanel } from '../voice/VoiceCallPanel';

export function Header() {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              🏥 Healthcare AI Assistant
            </h1>
          </div>
          <div className="flex-1 max-w-md">
            <VoiceCallPanel />
          </div>
        </div>
      </div>
    </header>
  );
}

