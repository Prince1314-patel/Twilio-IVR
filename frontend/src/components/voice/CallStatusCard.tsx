/**
 * Call Status Card Component
 * ==========================
 * 
 * Component for displaying call status information.
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Phone, PhoneOff, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { useVoice } from '@/store/context/VoiceContext';
import { format } from 'date-fns';

export function CallStatusCard() {
  const { callStatus, callSid, clearCall } = useVoice();

  if (!callSid && !callStatus) {
    return null;
  }

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: React.ReactNode; label: string }> = {
      'queued': { variant: 'secondary', icon: <Clock className="h-3 w-3" />, label: 'Queued' },
      'ringing': { variant: 'default', icon: <Phone className="h-3 w-3" />, label: 'Ringing' },
      'in-progress': { variant: 'default', icon: <Phone className="h-3 w-3" />, label: 'In Progress' },
      'completed': { variant: 'default', icon: <CheckCircle2 className="h-3 w-3" />, label: 'Completed' },
      'busy': { variant: 'destructive', icon: <XCircle className="h-3 w-3" />, label: 'Busy' },
      'failed': { variant: 'destructive', icon: <XCircle className="h-3 w-3" />, label: 'Failed' },
      'no-answer': { variant: 'destructive', icon: <XCircle className="h-3 w-3" />, label: 'No Answer' },
      'canceled': { variant: 'destructive', icon: <XCircle className="h-3 w-3" />, label: 'Canceled' },
    };

    const statusInfo = statusMap[status.toLowerCase()] || { variant: 'secondary' as const, icon: null, label: status };
    return (
      <Badge variant={statusInfo.variant} className="flex items-center gap-1">
        {statusInfo.icon}
        {statusInfo.label}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Call Status</CardTitle>
          {callStatus && ['completed', 'failed', 'busy', 'no-answer', 'canceled'].includes(callStatus.status.toLowerCase()) && (
            <Button variant="ghost" size="sm" onClick={clearCall}>
              <PhoneOff className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {callStatus && (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Status:</span>
              {getStatusBadge(callStatus.status)}
            </div>
            {callStatus.duration && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Duration:</span>
                <span className="text-sm font-medium">{callStatus.duration} seconds</span>
              </div>
            )}
            {callStatus.from && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">From:</span>
                <span className="text-sm font-medium">{callStatus.from}</span>
              </div>
            )}
            {callStatus.to && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">To:</span>
                <span className="text-sm font-medium">{callStatus.to}</span>
              </div>
            )}
          </>
        )}
        {callSid && (
          <div className="pt-2 border-t">
            <span className="text-xs text-muted-foreground">Call ID: {callSid.slice(0, 20)}...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

