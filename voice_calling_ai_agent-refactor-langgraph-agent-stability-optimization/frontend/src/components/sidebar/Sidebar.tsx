/**
 * Sidebar Component
 * ================
 * 
 * Main sidebar component with all sections.
 */

import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { CallStatusSection } from './CallStatusSection';
import { AboutSection } from './AboutSection';
import { QuickActions } from './QuickActions';
import { UserLookup } from './UserLookup';

export function Sidebar() {
  return (
    <ScrollArea className="h-full">
      <div className="space-y-4 p-4">
        <CallStatusSection />
        <Separator />
        <UserLookup />
        <Separator />
        <AboutSection />
        <Separator />
        <QuickActions />
      </div>
    </ScrollArea>
  );
}
