/**
 * About Section Component
 * =======================
 * 
 * About section showing application features.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Calendar, CheckSquare, RefreshCw, X, Phone } from 'lucide-react';

export function AboutSection() {
  const features = [
    { icon: Calendar, text: 'Schedule appointments' },
    { icon: CheckSquare, text: 'Check availability' },
    { icon: RefreshCw, text: 'Update appointments' },
    { icon: X, text: 'Cancel appointments' },
    { icon: Phone, text: 'Voice calling support' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">About</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">
          This AI assistant helps you:
        </p>
        <ul className="space-y-2">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <li key={index} className="flex items-center gap-2 text-sm">
                <Icon className="h-4 w-4 text-primary" />
                <span>{feature.text}</span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
