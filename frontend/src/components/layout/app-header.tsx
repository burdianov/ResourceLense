import { Bell, ChevronDown, LogOut, Menu, UserRound } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { NavigationLink } from "@/components/layout/nav-link";
import { useVisibleNavigation } from "@/components/layout/navigation";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  useCurrentUser,
  useLogout,
} from "@/features/auth/use-current-user";

export function AppHeader() {
  const navigate = useNavigate();
  const { data: currentUser } = useCurrentUser();
  const logout = useLogout();
  const { primary, administration } = useVisibleNavigation();

  const [navigationOpen, setNavigationOpen] = useState(false);

  async function handleLogout() {
    await logout.mutateAsync();
    navigate("/login", { replace: true });
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b bg-background px-4 md:px-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="Open navigation"
          onClick={() => setNavigationOpen(true)}
        >
          <Menu className="size-4" />
        </Button>

        <span className="font-medium lg:hidden">ResourceLense</span>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="size-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button variant="ghost" className="gap-2" />}
          >
            <div className="flex size-7 items-center justify-center rounded-full bg-muted">
              <UserRound className="size-4" />
            </div>

            <span className="hidden text-sm md:inline">
              {currentUser?.full_name ?? "User"}
            </span>

            <ChevronDown className="size-3.5 text-muted-foreground" />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="min-w-56">
            <DropdownMenuGroup>
              <DropdownMenuLabel>
                <span className="block truncate font-medium text-foreground">
                  {currentUser?.full_name ?? "User"}
                </span>

                <span className="block truncate font-normal">
                  {currentUser?.email}
                </span>
              </DropdownMenuLabel>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              variant="destructive"
              onClick={handleLogout}
              disabled={logout.isPending}
            >
              <LogOut />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Sheet open={navigationOpen} onOpenChange={setNavigationOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetHeader className="border-b">
            <SheetTitle>ResourceLense</SheetTitle>

            <SheetDescription className="sr-only">
              Main navigation
            </SheetDescription>
          </SheetHeader>

          <nav className="flex-1 space-y-1 overflow-y-auto p-3">
            {primary.map((item) => (
              <NavigationLink
                key={item.href}
                item={item}
                onNavigate={() => setNavigationOpen(false)}
              />
            ))}

            {administration.length > 0 ? (
              <div className="space-y-1 pt-3">
                <div className="px-3 pb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  Administration
                </div>

                {administration.map((item) => (
                  <NavigationLink
                    key={item.href}
                    item={item}
                    onNavigate={() => setNavigationOpen(false)}
                  />
                ))}
              </div>
            ) : null}
          </nav>
        </SheetContent>
      </Sheet>
    </header>
  );
}
