/**
 * Header Component
 * ================
 * 
 * Main application header with title.
 */

export function Header() {
  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            🏥 Healthcare AI Assistant
          </h1>
        </div>
      </div>
    </header>
  );
}
