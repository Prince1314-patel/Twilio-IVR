/**
 * Footer Component
 * ================
 * 
 * Application footer with version information.
 */

import { APP_NAME, APP_VERSION } from '@/utils/constants';

export function Footer() {
  return (
    <footer className="border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 mt-auto">
      <div className="container mx-auto px-4 py-4">
        <p className="text-center text-sm text-muted-foreground">
          {APP_NAME} v{APP_VERSION} | Powered by FastAPI & React
        </p>
      </div>
    </footer>
  );
}
