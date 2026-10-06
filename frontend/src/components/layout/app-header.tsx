import { Bell, ChevronDown, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";

export function AppHeader() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background px-4 md:px-6">
      <div>
        <span className="font-medium lg:hidden">ResourceLense</span>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="size-4" />
        </Button>

        <Button variant="ghost" className="gap-2">
          <div className="flex size-7 items-center justify-center rounded-full bg-muted">
            <UserRound className="size-4" />
          </div>

          <span className="hidden text-sm md:inline">User</span>

          <ChevronDown className="size-3.5 text-muted-foreground" />
        </Button>
      </div>
    </header>
  );
}
