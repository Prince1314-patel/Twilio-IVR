import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AssistantUiState } from "@/features/assistant/types";
import { Sparkles, ShieldCheck } from "lucide-react";

interface AssistantHeaderProps {
  sessionId: string;
  uiState: AssistantUiState;
  isAuthenticated: boolean;
  userName?: string | null;
  onOpenPrompts: () => void;
}

const UI_STATE_LABEL: Record<AssistantUiState, string> = {
  onboarding: "Identity check",
  idle: "Ready",
  composing: "Drafting",
  sending: "Responding",
  error: "Needs attention",
};

export function AssistantHeader({
  sessionId,
  uiState,
  isAuthenticated,
  userName,
  onOpenPrompts,
}: AssistantHeaderProps) {
  const shortSessionId = sessionId.slice(0, 8);

  return (
    <header className="glass-surface shrink-0 z-20 rounded-3xl border border-border/70 px-5 py-4 shadow-sm md:px-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="font-display text-2xl leading-tight text-foreground md:text-3xl">
            CareFlow Assistant
          </p>
          <p className="text-sm text-foreground/80">
            Secure conversational support for appointments and scheduling.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="gap-1.5 border-border/70 text-xs">
            <ShieldCheck className="h-3.5 w-3.5" />
            Secure session
          </Badge>
          <Badge
            variant="secondary"
            className="text-xs font-medium text-secondary-foreground"
          >
            {UI_STATE_LABEL[uiState]}
          </Badge>
          <Badge
            variant="outline"
            className="font-mono text-[11px] tracking-wide text-muted-foreground"
          >
            session {shortSessionId}
          </Badge>
          {isAuthenticated && (
            <Badge variant="outline" className="text-xs">
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              {userName || "Verified user"}
            </Badge>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row lg:hidden">
        <Button
          onClick={onOpenPrompts}
          variant="outline"
          className="sm:w-auto"
        >
          <Sparkles className="mr-2 h-4 w-4" />
          Guided Prompts
        </Button>
      </div>
    </header>
  );
}
