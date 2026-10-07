import { Settings } from "lucide-react";

import { NavigationLink } from "@/components/layout/nav-link";
import { useVisibleNavigation } from "@/components/layout/navigation";

export function AppSidebar() {
  const { primary, administration } = useVisibleNavigation();

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-background lg:flex lg:flex-col">
      <div className="flex h-16 items-center border-b px-6">
        <span className="text-xl font-semibold tracking-tight">
          ResourceLense
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {primary.map((item) => (
          <NavigationLink key={item.href} item={item} />
        ))}
      </nav>

      {administration.length > 0 ? (
        <div className="border-t p-3">
          <div className="flex items-center gap-3 px-3 pb-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
            <Settings className="size-3.5" />
            Administration
          </div>

          <div className="space-y-1">
            {administration.map((item) => (
              <NavigationLink key={item.href} item={item} />
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
