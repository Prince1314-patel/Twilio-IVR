import type { ChatMessage } from "@/types/chat";
import type {
  MessageGroupPosition,
  TimelineMessageViewModel,
} from "@/features/assistant/types";

function resolveGroupPosition(
  previousRole: ChatMessage["role"] | undefined,
  currentRole: ChatMessage["role"],
  nextRole: ChatMessage["role"] | undefined
): MessageGroupPosition {
  const isPrevSame = previousRole === currentRole;
  const isNextSame = nextRole === currentRole;

  if (isPrevSame && isNextSame) return "middle";
  if (isPrevSame && !isNextSame) return "end";
  if (!isPrevSame && isNextSame) return "start";
  return "single";
}

export function mapChatMessagesToTimeline(
  messages: ChatMessage[]
): TimelineMessageViewModel[] {
  return messages.map((message, index) => {
    const previousRole = messages[index - 1]?.role;
    const nextRole = messages[index + 1]?.role;

    return {
      id: `${index}-${message.role}-${message.timestamp ?? "no-time"}`,
      role: message.role,
      content: message.content,
      timestamp: message.timestamp,
      showTimestamp: !nextRole || nextRole !== message.role,
      groupPosition: resolveGroupPosition(previousRole, message.role, nextRole),
    };
  });
}

