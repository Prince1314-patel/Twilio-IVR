import { useEffect, useMemo, useRef } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import type { TimelineProps } from "@/features/assistant/types";
import { cn } from "@/utils";
import { format } from "date-fns";
import { Bot, User } from "lucide-react";
import { motion } from "framer-motion";

function resolveBubbleShape(groupPosition: string, isUser: boolean) {
  if (groupPosition === "single") {
    return "rounded-2xl";
  }

  if (isUser) {
    if (groupPosition === "start") return "rounded-2xl rounded-br-md";
    if (groupPosition === "middle") return "rounded-2xl rounded-br-md";
    return "rounded-2xl rounded-tr-md";
  }

  if (groupPosition === "start") return "rounded-2xl rounded-bl-md";
  if (groupPosition === "middle") return "rounded-2xl rounded-bl-md";
  return "rounded-2xl rounded-tl-md";
}

export function ConversationTimeline({ messages, isSending = false }: TimelineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  return (
    <div
      ref={containerRef}
      className="relative flex-1 overflow-x-hidden overflow-y-auto px-4 py-5 md:px-6 md:py-6"
    >
      {!hasMessages && (
        <div className="mx-auto mt-16 max-w-xl rounded-3xl border border-border/70 bg-card/90 p-6 text-center shadow-sm">
          <p className="font-display text-2xl text-foreground">
            Your appointment assistant is ready
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Ask naturally about booking, cancelling, rescheduling, or checking
            appointments.
          </p>
        </div>
      )}

      <div className="mx-auto w-full max-w-3xl space-y-3">
        {messages.map((message) => {
          const isUser = message.role === "user";
          const bubbleShape = resolveBubbleShape(message.groupPosition, isUser);

          return (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.24 }}
              className={cn(
                "flex min-w-0 items-end gap-2",
                isUser ? "justify-end" : "justify-start"
              )}
            >
              {!isUser && (
                <Avatar className="mb-0.5 h-8 w-8">
                  <AvatarFallback className="bg-accent text-accent-foreground">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}

              <div
                className={cn(
                  "min-w-0 max-w-[82%] space-y-1 md:max-w-[72%]",
                  isUser && "items-end"
                )}
              >
                <div
                  className={cn(
                    "overflow-hidden px-4 py-2.5 text-sm leading-relaxed shadow-sm",
                    bubbleShape,
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "border border-border/60 bg-card text-card-foreground"
                  )}
                >
                  <p className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
                    {message.content}
                  </p>
                </div>
                {message.showTimestamp && message.timestamp && (
                  <p
                    className={cn(
                      "px-1 text-[11px] text-muted-foreground",
                      isUser ? "text-right" : "text-left"
                    )}
                  >
                    {format(new Date(message.timestamp), "HH:mm")}
                  </p>
                )}
              </div>

              {isUser && (
                <Avatar className="mb-0.5 h-8 w-8">
                  <AvatarFallback className="bg-primary/20 text-primary">
                    <User className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
            </motion.div>
          );
        })}

        {isSending && (
          <div className="flex items-end gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-accent text-accent-foreground">
                <Bot className="h-4 w-4" />
              </AvatarFallback>
            </Avatar>
            <div className="space-y-2 rounded-2xl rounded-bl-md border border-border/60 bg-card px-4 py-3">
              <Skeleton className="h-3.5 w-24 bg-muted" />
              <Skeleton className="h-3.5 w-16 bg-muted" />
            </div>
          </div>
        )}
      </div>

      <div ref={endRef} />
    </div>
  );
}
