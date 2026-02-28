import { useMemo, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { OnboardingProps } from "@/features/assistant/types";
import { identifyUser } from "@/services/chat";
import { Loader2, LockKeyhole, Phone, ShieldCheck } from "lucide-react";

export function OnboardingPanel({
  sessionId,
  initialPhoneNumber = "",
  onAuthenticated,
}: OnboardingProps) {
  const [phoneNumber, setPhoneNumber] = useState(initialPhoneNumber);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValidPhone = useMemo(() => {
    const cleaned = phoneNumber.replace(/[\s-]/g, "");
    return /^\+?[0-9]{10,15}$/.test(cleaned);
  }, [phoneNumber]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!isValidPhone) {
      setError("Enter a valid phone number in international format.");
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      const sanitizedPhoneNumber = phoneNumber.trim();
      const response = await identifyUser(sanitizedPhoneNumber, sessionId);
      onAuthenticated({
        phoneNumber: sanitizedPhoneNumber,
        user: response.user,
      });
    } catch (err: unknown) {
      const fallbackMessage = "Unable to verify identity. Please try again.";
      const message =
        typeof err === "object" &&
        err !== null &&
        "detail" in err &&
        typeof (err as { detail?: string }).detail === "string"
          ? (err as { detail: string }).detail
          : fallbackMessage;
      setError(message);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="flex h-full min-h-[460px] items-center justify-center p-4 md:p-8">
      <Card className="w-full max-w-xl border-border/70 bg-card/95 shadow-lg">
        <CardHeader className="space-y-3 pb-2">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-border/70 bg-background px-3 py-1 text-xs text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5" />
            Privacy-first verification
          </div>
          <CardTitle className="font-display text-2xl">
            Verify your identity to continue
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            We use your phone number to safely retrieve appointment context and
            protect your medical scheduling information.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground" htmlFor="phone">
                Mobile number
              </label>
              <div className="relative">
                <Phone className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="phone"
                  value={phoneNumber}
                  onChange={(event) => setPhoneNumber(event.target.value)}
                  placeholder="+1234567890"
                  className="h-11 rounded-xl border-border/80 pl-9"
                  autoFocus
                />
              </div>
            </div>

            {error && (
              <p className="rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            )}

            <Button
              type="submit"
              className="h-11 w-full rounded-xl"
              disabled={isVerifying || !isValidPhone}
            >
              {isVerifying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying
                </>
              ) : (
                <>
                  <LockKeyhole className="mr-2 h-4 w-4" />
                  Continue to assistant
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
