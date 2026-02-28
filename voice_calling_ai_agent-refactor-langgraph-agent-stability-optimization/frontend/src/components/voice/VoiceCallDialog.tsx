/**
 * Voice Call Dialog Component
 * ==========================
 * 
 * Dialog component for initiating voice calls (reusable, without trigger button).
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Phone, Loader2, AlertCircle } from 'lucide-react';
import { PhoneInput } from './PhoneInput';
import { useVoiceCallInitiate } from '@/hooks/useVoiceCall';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { validatePhoneNumber } from '@/utils/helpers';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface VoiceCallDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function VoiceCallDialog({ open, onOpenChange }: VoiceCallDialogProps) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const { initiateVoiceCall, isInitiating, error, clearError } = useVoiceCallInitiate();

  const handleInitiateCall = async () => {
    if (!validatePhoneNumber(phoneNumber)) {
      return;
    }

    const success = await initiateVoiceCall(phoneNumber);
    if (success) {
      setPhoneNumber('');
      onOpenChange(false);
    }
  };

  const isValid = validatePhoneNumber(phoneNumber);

  const handleOpenChange = (newOpen: boolean) => {
    onOpenChange(newOpen);
    if (!newOpen) {
      // Clear error and phone number when dialog closes
      clearError();
      setPhoneNumber('');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Initiate Voice Call</DialogTitle>
          <DialogDescription>
            Enter your phone number with country code (E.164 format) to receive a call from the AI assistant.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Phone Number</label>
            <PhoneInput
              value={phoneNumber}
              onChange={setPhoneNumber}
              placeholder="+1234567890"
              disabled={isInitiating}
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!error && phoneNumber && isValid && (
            <div className="text-xs text-muted-foreground space-y-1">
              <p className="font-medium">Call Instructions:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Answer your phone when it rings</li>
                <li>The AI assistant will greet you</li>
                <li>You can speak naturally about appointments</li>
                <li>Say "book an appointment" to start scheduling</li>
              </ul>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            onClick={handleInitiateCall}
            disabled={!isValid || isInitiating}
            className="w-full sm:w-auto"
          >
            {isInitiating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Initiating Call...
              </>
            ) : (
              <>
                <Phone className="mr-2 h-4 w-4" />
                Call Me
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
