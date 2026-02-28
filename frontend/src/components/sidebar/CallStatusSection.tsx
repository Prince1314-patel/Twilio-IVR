/**
 * Call Status Section Component
 * =============================
 * 
 * Sidebar section for displaying call status.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useVoice } from '@/store/context/VoiceContext';
import { Phone, PhoneOff } from 'lucide-react';
import { CallStatusCard } from '@/components/voice/CallStatusCard';

export function CallStatusSection() {
  const { isCallActive } = useVoice();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Call Status</CardTitle>
          {isCallActive && (
            <Badge variant="default" className="flex items-center gap-1">
              <Phone className="h-3 w-3" />
              Active
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isCallActive ? (
          <CallStatusCard />
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
            <PhoneOff className="h-12 w-12 mb-2 opacity-50" />
            <p className="text-sm">No active call</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
