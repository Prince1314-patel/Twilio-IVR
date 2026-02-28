import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { ComposerProps } from "@/features/assistant/types";
import { CHAT_MESSAGE_MAX_LENGTH } from "@/utils/constants";
import { cn } from "@/utils";
import { Loader2, SendHorizontal, Sparkles } from "lucide-react";

export function ComposerDock({
  onSendMessage,
  onDraftStateChange,
  onOpenPrompts,
  disabled = false,
  isSending = false,
}: ComposerProps) {
  const [draft, setDraft] = useState("");

  useEffect(() => {
    onDraftStateChange?.(draft.trim().length > 0);
  }, [draft, onDraftStateChange]);

  const remaining = CHAT_MESSAGE_MAX_LENGTH - draft.length;
  const isNearLimit = remaining < 120;

  const handleSend = async () => {
    if (!draft.trim() || disabled || isSending) return;
    const payload = draft.trim();
    setDraft("");
    await onSendMessage(payload);
  };

  return (
    <div className="border-t border-border/70 bg-background/80 px-4 py-4 backdrop-blur md:px-6">
      <div className="mx-auto w-full max-w-3xl space-y-3">
        <div className="relative">
          <textarea
            value={draft}
            onChange={(event) => {
              if (event.target.value.length <= CHAT_MESSAGE_MAX_LENGTH) {
                setDraft(event.target.value);
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Type your question about booking, rescheduling, or appointment status..."
            disabled={disabled || isSending}
            className="min-h-[54px] w-full resize-none rounded-2xl border border-input bg-card px-4 py-3 pr-14 text-sm text-foreground shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
            rows={2}
          />
          <Button
            size="icon"
            className="absolute top-1/2 -translate-y-1/2 right-2 h-9 w-9 rounded-xl"
            onClick={() => void handleSend()}
            disabled={disabled || isSending || !draft.trim()}
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <SendHorizontal className="h-4 w-4" />
            )}
          </Button>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Press <kbd className="rounded border bg-muted px-1 py-0.5">Enter</kbd>{" "}
            to send and <kbd className="rounded border bg-muted px-1 py-0.5">Shift + Enter</kbd>{" "}
            for a new line.
          </p>
          <p
            className={cn(
              "text-xs text-muted-foreground",
              isNearLimit && "font-semibold",
              remaining < 20 && "text-destructive"
            )}
          >
            {remaining}
          </p>
        </div>

        <Button
          onClick={onOpenPrompts}
          variant="outline"
          size="sm"
          className="w-full lg:hidden"
        >
          <Sparkles className="mr-2 h-4 w-4" />
          Open guided prompts
        </Button>
      </div>
    </div>
  );
}
