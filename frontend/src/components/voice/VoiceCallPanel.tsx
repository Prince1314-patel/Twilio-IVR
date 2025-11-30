/**
 * Voice Call Panel Component
 * ==========================
 * 
 * Panel for initiating voice calls.
 */

import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Phone, Loader2, AlertCircle } from 'lucide-react';
import { PhoneInput } from './PhoneInput';
import { useVoiceCallInitiate } from '@/hooks/useVoiceCall';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { validatePhoneNumber } from '@/utils/helpers';

export function VoiceCallPanel() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const { initiateVoiceCall, isInitiating, error, clearError } = useVoiceCallInitiate();

  const handleInitiateCall = async () => {
    if (!validatePhoneNumber(phoneNumber)) {
      return;
    }

    const success = await initiateVoiceCall(phoneNumber);
    if (success) {
      setPhoneNumber('');
    }
  };

  const isValid = validatePhoneNumber(phoneNumber);

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Phone Number</label>
            <PhoneInput
              value={phoneNumber}
              onChange={setPhoneNumber}
              placeholder="+1234567890"
              disabled={isInitiating}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Enter your phone number with country code (E.164 format)
            </p>
          </div>

          <Button
            onClick={handleInitiateCall}
            disabled={!isValid || isInitiating}
            className="w-full"
            size="lg"
          >
            {isInitiating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Initiating Call...
              </>
            ) : (
              <>
                <Phone className="mr-2 h-4 w-4" />
                Get Voice Call
              </>
            )}
          </Button>

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
      </CardContent>
    </Card>
  );
}

