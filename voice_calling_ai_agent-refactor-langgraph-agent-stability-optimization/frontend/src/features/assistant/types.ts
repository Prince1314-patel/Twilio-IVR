import type { UserDetails } from "@/services/chat";
import type { ChatMessage } from "@/types/chat";

export type AssistantUiState =
  | "onboarding"
  | "idle"
  | "composing"
  | "sending"
  | "error";

export interface PromptAction {
  id: string;
  label: string;
  prompt: string;
  description: string;
}

export type MessageGroupPosition = "single" | "start" | "middle" | "end";

export interface TimelineMessageViewModel {
  id: string;
  role: ChatMessage["role"];
  content: string;
  timestamp?: string;
  showTimestamp: boolean;
  groupPosition: MessageGroupPosition;
}

export interface ComposerProps {
  onSendMessage: (message: string) => Promise<void> | void;
  onDraftStateChange?: (isComposing: boolean) => void;
  onOpenPrompts?: () => void;
  disabled?: boolean;
  isSending?: boolean;
}

export interface TimelineProps {
  messages: TimelineMessageViewModel[];
  isSending?: boolean;
}

export interface OnboardingProps {
  sessionId: string;
  initialPhoneNumber?: string;
  onAuthenticated: (payload: {
    phoneNumber: string;
    user: UserDetails;
  }) => void;
}

export interface VoiceTrayState {
  isCallActive: boolean;
  statusLabel: string;
  callSid: string | null;
}

export interface UtilityTrayProps {
  onStartNewSession: () => Promise<void> | void;
  isVoiceDialogOpen: boolean;
  onVoiceDialogOpenChange: (open: boolean) => void;
  isStartingNewSession?: boolean;
}
