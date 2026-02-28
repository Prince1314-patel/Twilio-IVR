import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Phone, User as UserIcon, Loader2, Search } from 'lucide-react';
import { lookupUser, type UserDetails } from '@/services/chat';

export function UserLookup() {
    const [phoneNumber, setPhoneNumber] = useState('');
    const [loading, setLoading] = useState(false);
    const [user, setUser] = useState<UserDetails | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleLookup = async () => {
        if (!phoneNumber.trim()) return;

        setLoading(true);
        setError(null);
        setUser(null);

        try {
            const data = await lookupUser(phoneNumber);
            setUser(data);
        } catch (err: any) {
            console.error("User lookup failed:", err);
            setError(err.detail || "User not found or error occurred");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2 mb-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    User Lookup
                </h3>
            </div>

            <div className="flex gap-2">
                <Input
                    placeholder="Enter phone number..."
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLookup()}
                    className="h-9"
                />
                <Button
                    size="sm"
                    onClick={handleLookup}
                    disabled={loading || !phoneNumber.trim()}
                    className="h-9 w-9 p-0"
                >
                    {loading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        <Search className="h-4 w-4" />
                    )}
                </Button>
            </div>

            {error && (
                <div className="text-xs text-destructive bg-destructive/10 p-2 rounded-md">
                    {error}
                </div>
            )}

            {user && (
                <Card className="bg-card/50">
                    <CardContent className="p-3 space-y-2 text-sm">
                        <div className="flex items-center gap-2">
                            <UserIcon className="h-3.5 w-3.5 text-primary" />
                            <span className="font-medium">{user.full_name || 'Unknown Name'}</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <Phone className="h-3.5 w-3.5" />
                            <span>{user.mobile_number}</span>
                        </div>
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <span className="text-xs text-muted-foreground/70">ID: {user.id}</span>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
