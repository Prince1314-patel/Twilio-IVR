import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Phone, Loader2, Lock } from 'lucide-react';
import { identifyUser } from '@/services/chat';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog"

interface IdentityModalProps {
    open: boolean;
    sessionId: string;
    onAuthenticated: (user: any) => void;
}

export function IdentityModal({ open, sessionId, onAuthenticated }: IdentityModalProps) {
    const [phoneNumber, setPhoneNumber] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isValidPhone = (phone: string) => {
        const phoneRegex = /^\+?[0-9]{10,15}$/;
        return phoneRegex.test(phone.replace(/[\s-]/g, ''));
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!phoneNumber.trim()) return;

        if (!isValidPhone(phoneNumber)) {
            setError("Please enter a valid phone number (e.g., +1234567890)");
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const { user } = await identifyUser(phoneNumber, sessionId);
            onAuthenticated(user);
        } catch (err: any) {
            console.error("Identity verification failed:", err);
            setError(err.detail || "Verification failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open}>
            <DialogContent className="sm:max-w-md" onPointerDownOutside={(e) => e.preventDefault()} onEscapeKeyDown={(e) => e.preventDefault()}>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Lock className="h-5 w-5 text-primary" />
                        Identity Verification
                    </DialogTitle>
                    <DialogDescription>
                        Please enter your phone number to access the secure chat.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4 py-4">
                    <div className="space-y-2">
                        <div className="relative">
                            <Phone className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="+1234567890"
                                className="pl-9"
                                value={phoneNumber}
                                onChange={(e) => setPhoneNumber(e.target.value)}
                                autoFocus
                            />
                        </div>
                        {error && (
                            <p className="text-sm text-destructive font-medium">{error}</p>
                        )}
                    </div>

                    <DialogFooter>
                        <Button type="submit" className="w-full" disabled={loading || !phoneNumber.trim()}>
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Verifying...
                                </>
                            ) : (
                                'Continue to Chat'
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
