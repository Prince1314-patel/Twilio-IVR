/**
 * Quick Actions Component
 * ======================
 * 
 * Quick action buttons for session management.
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RotateCcw } from 'lucide-react';
import { useSessionManagement } from '@/hooks/useSession';
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
      </CardContent>
    </Card>
  );
}

