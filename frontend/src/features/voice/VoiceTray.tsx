import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { VoiceTrayState } from "@/features/assistant/types";
import { VoiceCallDialog } from "@/components/voice/VoiceCallDialog";
import { useVoice } from "@/store/context";
import { PhoneCall, PhoneForwarded, PhoneOff } from "lucide-react";
import { useMemo, useState } from "react";

interface VoiceTrayProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

function getStatusLabel(status: string | null): string {
  if (!status) return "Idle";

  const map: Record<string, string> = {
    queued: "Queued",
    ringing: "Ringing",
    "in-progress": "In progress",
    completed: "Completed",
    busy: "Busy",
    failed: "Failed",
    "no-answer": "No answer",
    canceled: "Canceled",
  };

  const normalized = status.toLowerCase();
  return map[normalized] ?? status;
}

export function VoiceTray({ open, onOpenChange }: VoiceTrayProps) {
  const { callSid, callStatus, isCallActive } = useVoice();
  const [uncontrolledOpen, setUncontrolledOpen] = useState(false);

  const isControlled = typeof open === "boolean";
  const isDialogOpen = isControlled ? open : uncontrolledOpen;

  const setIsDialogOpen = (nextOpen: boolean) => {
    if (!isControlled) {
      setUncontrolledOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  };

  const state: VoiceTrayState = useMemo(
    () => ({
      isCallActive,
      statusLabel: getStatusLabel(callStatus?.status ?? null),
      callSid,
    }),
    [callSid, callStatus?.status, isCallActive]
  );

  return (
    <Card className="border-border/70 bg-card/95 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="font-display text-lg">Voice support</CardTitle>
        <CardDescription className="text-xs">
          Optional phone call if you prefer voice guidance.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 pb-3">
        <div className="flex items-center justify-between rounded-xl border border-border/70 bg-background/70 px-3 py-2">
          <div className="flex items-center gap-2 text-sm text-foreground">
            {state.isCallActive ? (
              <PhoneForwarded className="h-4 w-4 text-primary" />
            ) : (
              <PhoneOff className="h-4 w-4 text-muted-foreground" />
            )}
            Call status
          </div>
          <Badge variant={state.isCallActive ? "default" : "secondary"}>
            {state.statusLabel}
          </Badge>
        </div>

        {state.callSid && (
          <p className="font-mono text-[11px] text-muted-foreground">
            {state.callSid.slice(0, 20)}...
          </p>
        )}

        <Button
          className="w-full rounded-xl"
          onClick={() => {
            setIsDialogOpen(true);
          }}
          variant="outline"
        >
          <PhoneCall className="mr-2 h-4 w-4" />
          Start voice call
        </Button>

        <VoiceCallDialog open={isDialogOpen} onOpenChange={setIsDialogOpen} />
      </CardContent>
    </Card>
  );
}
