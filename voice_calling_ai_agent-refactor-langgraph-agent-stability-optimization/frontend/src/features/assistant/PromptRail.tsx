import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PromptAction } from "@/features/assistant/types";
import {
  CalendarPlus,
  CalendarClock,
  CalendarX2,
  ClipboardList,
} from "lucide-react";

interface PromptRailProps {
  actions: PromptAction[];
  onSelectPrompt: (prompt: string) => void;
  title?: string;
}

function getPromptIcon(promptId: string) {
  if (promptId === "book") return CalendarPlus;
  if (promptId === "reschedule") return CalendarClock;
  if (promptId === "cancel") return CalendarX2;
  return ClipboardList;
}

export function PromptRail({
  actions,
  onSelectPrompt,
  title = "Guided prompts",
}: PromptRailProps) {
  return (
    <Card className="border-border/70 bg-card/95 shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="font-display text-lg">{title}</CardTitle>
        <p className="text-xs text-muted-foreground">
          Use a starter action for faster conversations.
        </p>
      </CardHeader>
      <CardContent className="space-y-1.5 pb-3">
        {actions.map((action) => {
          const Icon = getPromptIcon(action.id);
          return (
            <Button
              key={action.id}
              variant="outline"
              onClick={() => onSelectPrompt(action.prompt)}
              className="h-auto w-full items-start justify-start rounded-xl border-border/70 px-3 py-2 text-left whitespace-normal break-words"
            >
              <Icon className="mr-2 mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span className="space-y-0.5">
                <span className="block text-sm font-semibold text-foreground">
                  {action.label}
                </span>
                <span className="block text-xs font-normal text-muted-foreground">
                  {action.description}
                </span>
              </span>
            </Button>
          );
        })}
      </CardContent>
    </Card>
  );
}
