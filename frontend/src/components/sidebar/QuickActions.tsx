/**
 * Quick Actions Component
 * ======================
 * 
 * Quick action buttons for session management.
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RotateCcw, History } from 'lucide-react';
import { useSessionManagement } from '@/hooks/useSession';
import { useChat } from '@/store/context';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export function QuickActions() {
  const { startNewSession } = useSessionManagement();
  const { messages } = useChat();
  const [isStartingNewSession, setIsStartingNewSession] = useState(false);

  const handleNewSession = async () => {
    setIsStartingNewSession(true);
    await startNewSession();
    setIsStartingNewSession(false);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="outline"
              className="w-full justify-start"
              disabled={isStartingNewSession}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              New Chat Session
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Start New Session?</AlertDialogTitle>
              <AlertDialogDescription>
                This will clear your current conversation history and start a fresh session.
                Are you sure you want to continue?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleNewSession}>
                Start New Session
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <Button
          variant="outline"
          className="w-full justify-start"
          disabled={messages.length === 0}
          onClick={() => {
            // Could open a dialog to show full history
            console.log('Chat history:', messages);
          }}
        >
          <History className="mr-2 h-4 w-4" />
          View Chat History ({messages.length})
        </Button>
      </CardContent>
    </Card>
  );
}

