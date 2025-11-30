/**
 * Message Bubble Component
 * ========================
 * 
 * Individual message bubble component for chat messages.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/utils';
import type { ChatMessage } from '@/types/chat';
import { format } from 'date-fns';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const timestamp = message.timestamp ? new Date(message.timestamp) : new Date();

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'flex gap-3 mb-4',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <Avatar className="h-8 w-8">
        <AvatarFallback className={cn(
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'
        )}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      <div className={cn(
        'flex flex-col max-w-[75%]',
        isUser ? 'items-end' : 'items-start'
      )}>
        <div
          className={cn(
            'rounded-2xl px-4 py-2 shadow-sm',
            isUser
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-muted-foreground rounded-tl-sm'
          )}
        >
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <span className="text-xs text-muted-foreground mt-1 px-1">
          {format(timestamp, 'HH:mm')}
        </span>
      </div>
    </motion.div>
  );
}

