import { NavLink } from "react-router-dom";

import type { NavItem } from "@/components/layout/navigation";
import { cn } from "@/lib/utils";

type NavigationLinkProps = {
  item: NavItem;
  onNavigate?: () => void;
};

export function NavigationLink({ item, onNavigate }: NavigationLinkProps) {
  const Icon = item.icon;

  return (
    <NavLink
      to={item.href}
      end={item.href === "/"}
      onClick={onNavigate}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
        )
      }
    >
      <Icon className="size-4" />
      {item.name}
    </NavLink>
  );
}
