import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { UtilityTrayProps } from "@/features/assistant/types";
import { VoiceTray } from "@/features/voice/VoiceTray";
import { Loader2, RotateCcw, BarChart3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function UtilityTray({
  onStartNewSession,
  isVoiceDialogOpen,
  onVoiceDialogOpenChange,
  isStartingNewSession = false,
}: UtilityTrayProps) {
  const navigate = useNavigate();

  return (
    <div className="space-y-3">
      <Card className="border-border/70 bg-card/95 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="font-display text-lg">Session controls</CardTitle>
          <CardDescription className="text-xs">
            Start a fresh conversation when needed.
          </CardDescription>
        </CardHeader>
        <CardContent className="pb-3 space-y-2">
          <Button
            variant="outline"
            className="w-full rounded-xl"
            onClick={() => void onStartNewSession()}
            disabled={isStartingNewSession}
          >
            {isStartingNewSession ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting new session
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                New chat session
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            className="w-full rounded-xl"
            onClick={() => navigate('/metrics')}
          >
            <BarChart3 className="mr-2 h-4 w-4" />
            View Metrics Dashboard
          </Button>
        </CardContent>
      </Card>

      <VoiceTray
        open={isVoiceDialogOpen}
        onOpenChange={onVoiceDialogOpenChange}
      />
    </div>
  );
}
