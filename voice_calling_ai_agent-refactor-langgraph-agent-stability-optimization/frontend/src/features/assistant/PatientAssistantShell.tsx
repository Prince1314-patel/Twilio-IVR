import { useEffect, useMemo, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useApp, useChat } from "@/store/context";
import { useChatMessage } from "@/hooks/useChat";
import { identifyUser, type UserDetails } from "@/services/chat";
import type { AssistantUiState } from "@/features/assistant/types";
import { mapChatMessagesToTimeline } from "@/features/assistant/mappers";
import { PROMPT_ACTIONS } from "@/features/assistant/constants";
import { AssistantHeader } from "@/features/assistant/AssistantHeader";
import { ConversationTimeline } from "@/features/assistant/ConversationTimeline";
import { ComposerDock } from "@/features/assistant/ComposerDock";
import { OnboardingPanel } from "@/features/assistant/OnboardingPanel";
import { PromptRail } from "@/features/assistant/PromptRail";
import { UtilityTray } from "@/features/assistant/UtilityTray";

const AUTH_STORAGE_PREFIX = "careflow-auth";

type PersistedAuth = {
  phoneNumber: string;
  user: UserDetails;
};

export function PatientAssistantShell() {
  const { sessionId, createNewSession } = useApp();
  const { messages } = useChat();
  const { sendChatMessage, isSending, error, clearError } = useChatMessage();

  const [isPromptSheetOpen, setIsPromptSheetOpen] = useState(false);
  const [isComposing, setIsComposing] = useState(false);
  const [isHydratingAuth, setIsHydratingAuth] = useState(true);
  const [isStartingNewSession, setIsStartingNewSession] = useState(false);
  const [isVoiceDialogOpen, setIsVoiceDialogOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authenticatedUser, setAuthenticatedUser] = useState<UserDetails | null>(null);
  const [phoneNumber, setPhoneNumber] = useState("");

  const authStorageKey = `${AUTH_STORAGE_PREFIX}:${sessionId}`;

  useEffect(() => {
    let isDisposed = false;

    async function hydrateAuthState() {
      setIsHydratingAuth(true);
      setIsAuthenticated(false);
      setAuthenticatedUser(null);

      const stored = localStorage.getItem(authStorageKey);
      if (!stored) {
        if (!isDisposed) setIsHydratingAuth(false);
        return;
      }

      try {
        const parsed = JSON.parse(stored) as PersistedAuth;
        if (!parsed.phoneNumber) {
          localStorage.removeItem(authStorageKey);
          if (!isDisposed) setIsHydratingAuth(false);
          return;
        }

        const response = await identifyUser(parsed.phoneNumber, sessionId);
        if (isDisposed) return;

        setPhoneNumber(parsed.phoneNumber);
        setAuthenticatedUser(response.user);
        setIsAuthenticated(true);
      } catch {
        localStorage.removeItem(authStorageKey);
      } finally {
        if (!isDisposed) setIsHydratingAuth(false);
      }
    }

    void hydrateAuthState();

    return () => {
      isDisposed = true;
    };
  }, [authStorageKey, sessionId]);

  const handleAuthenticated = (payload: {
    phoneNumber: string;
    user: UserDetails;
  }) => {
    setIsAuthenticated(true);
    setPhoneNumber(payload.phoneNumber);
    setAuthenticatedUser(payload.user);
    localStorage.setItem(authStorageKey, JSON.stringify(payload));
  };

  const handleSendMessage = async (content: string) => {
    clearError();
    await sendChatMessage(content);
  };

  const handlePromptSelect = async (prompt: string) => {
    if (!isAuthenticated || isSending) return;
    await handleSendMessage(prompt);
    setIsPromptSheetOpen(false);
  };

  const handleStartNewSession = async () => {
    setIsStartingNewSession(true);

    try {
      localStorage.removeItem(authStorageKey);
      await createNewSession();
      setIsAuthenticated(false);
      setAuthenticatedUser(null);
      setPhoneNumber("");
      setIsPromptSheetOpen(false);
      clearError();
    } finally {
      setIsStartingNewSession(false);
    }
  };

  const timelineMessages = useMemo(
    () => mapChatMessagesToTimeline(messages),
    [messages]
  );

  const uiState: AssistantUiState = useMemo(() => {
    if (!isAuthenticated) return "onboarding";
    if (error) return "error";
    if (isSending) return "sending";
    if (isComposing) return "composing";
    return "idle";
  }, [error, isAuthenticated, isComposing, isSending]);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-background">
      <div className="relative z-10 mx-auto flex h-full w-full max-w-[1320px] flex-col gap-4 px-4 py-4 md:px-6 md:py-6">
        <AssistantHeader
          sessionId={sessionId}
          uiState={uiState}
          isAuthenticated={isAuthenticated}
          userName={authenticatedUser?.full_name}
          onOpenPrompts={() => setIsPromptSheetOpen(true)}
        />

        <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
          <section className="glass-surface flex min-w-0 flex-col overflow-hidden rounded-3xl border border-border/70 shadow-sm relative h-full">
            {isHydratingAuth ? (
              <div className="space-y-4 p-6">
                <Skeleton className="h-8 w-2/3" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-48 w-full" />
              </div>
            ) : !isAuthenticated ? (
              <OnboardingPanel
                sessionId={sessionId}
                initialPhoneNumber={phoneNumber}
                onAuthenticated={handleAuthenticated}
              />
            ) : (
              <>
                <ConversationTimeline messages={timelineMessages} isSending={isSending} />
                {error && (
                  <p className="mx-6 mb-1 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                    {error}
                  </p>
                )}
                <ComposerDock
                  onSendMessage={handleSendMessage}
                  onDraftStateChange={setIsComposing}
                  onOpenPrompts={() => setIsPromptSheetOpen(true)}
                  isSending={isSending}
                  disabled={!isAuthenticated}
                />
              </>
            )}
          </section>

          <div className="space-y-4 lg:hidden">
            <UtilityTray
              onStartNewSession={handleStartNewSession}
              isVoiceDialogOpen={isVoiceDialogOpen}
              onVoiceDialogOpenChange={setIsVoiceDialogOpen}
              isStartingNewSession={isStartingNewSession}
            />
          </div>

          <aside className="hidden h-full lg:block overflow-hidden relative">
            <div className="flex flex-col space-y-4 pb-0">
              <PromptRail
                actions={PROMPT_ACTIONS}
                onSelectPrompt={(prompt) => void handlePromptSelect(prompt)}
              />
              <UtilityTray
                onStartNewSession={handleStartNewSession}
                isVoiceDialogOpen={isVoiceDialogOpen}
                onVoiceDialogOpenChange={setIsVoiceDialogOpen}
                isStartingNewSession={isStartingNewSession}
              />
            </div>
          </aside>
        </div>
      </div>

      <Dialog open={isPromptSheetOpen} onOpenChange={setIsPromptSheetOpen}>
        <DialogContent className="bottom-0 top-auto max-h-[80vh] translate-x-[-50%] translate-y-0 rounded-t-3xl rounded-b-none p-0 sm:max-w-xl">
          <DialogHeader className="px-6 pt-6">
            <DialogTitle className="font-display text-2xl">Guided prompts</DialogTitle>
            <DialogDescription>
              Choose a quick action to start the right appointment flow.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto px-6 pb-6 pt-2">
            <PromptRail
              actions={PROMPT_ACTIONS}
              onSelectPrompt={(prompt) => void handlePromptSelect(prompt)}
              title="Quick actions"
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
