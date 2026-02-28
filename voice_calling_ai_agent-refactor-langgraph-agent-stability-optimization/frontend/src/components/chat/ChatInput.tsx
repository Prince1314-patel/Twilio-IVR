/**
 * Chat Input Component
 * ====================
 * 
 * Input component for sending chat messages.
 */

import { useState, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Send, Loader2, Phone } from 'lucide-react';
import { cn } from '@/utils';
import { CHAT_MESSAGE_MAX_LENGTH } from '@/utils/constants';
import { VoiceCallDialog } from '@/components/voice/VoiceCallDialog';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSendMessage, isLoading = false, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isCallDialogOpen, setIsCallDialogOpen] = useState(false);

  const handleSend = () => {
    if (!message.trim() || isLoading || disabled) return;

    onSendMessage(message.trim());
    setMessage('');
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const remainingChars = CHAT_MESSAGE_MAX_LENGTH - message.length;
  const isNearLimit = remainingChars < 50;

  return (
    <div className="border-t bg-background p-4">
      <div className="flex gap-2 items-end">
        <div className="flex-1 relative">
          <Input
            value={message}
            onChange={(e) => {
              if (e.target.value.length <= CHAT_MESSAGE_MAX_LENGTH) {
                setMessage(e.target.value);
              }
            }}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here..."
            disabled={isLoading || disabled}
            className="pr-20"
            maxLength={CHAT_MESSAGE_MAX_LENGTH}
          />
          {isNearLimit && (
            <span className={cn(
              'absolute right-3 top-1/2 -translate-y-1/2 text-xs',
              remainingChars < 10 ? 'text-destructive' : 'text-muted-foreground'
            )}>
              {remainingChars}
            </span>
          )}
        </div>
        <Button
          size="icon"
          className="h-10 w-10"
          variant="outline"
          disabled={isLoading || disabled}
          onClick={() => setIsCallDialogOpen(true)}
        >
          <Phone className="h-4 w-4" />
        </Button>
        <VoiceCallDialog
          open={isCallDialogOpen}
          onOpenChange={setIsCallDialogOpen}
        />
        <Button
          onClick={handleSend}
          disabled={!message.trim() || isLoading || disabled}
          size="icon"
          className="h-10 w-10"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
