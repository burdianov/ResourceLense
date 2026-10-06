import {
  BarChart3,
  BriefcaseBusiness,
  LayoutDashboard,
  Settings,
  UsersRound,
} from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const navigation = [
  {
    name: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Planning",
    href: "/planning",
    icon: BarChart3,
  },
  {
    name: "Projects",
    href: "/projects",
    icon: BriefcaseBusiness,
  },
  {
    name: "Resources",
    href: "/resources",
    icon: UsersRound,
  },
  {
    name: "Reports",
    href: "/reports",
    icon: BarChart3,
  },
];

export function AppSidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-background lg:flex lg:flex-col">
      <div className="flex h-16 items-center border-b px-6">
        <span className="text-xl font-semibold tracking-tight">
          ResourceLense
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navigation.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.href}
              to={item.href}
              end={item.href === "/"}
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
        })}
      </nav>

      <div className="border-t p-3">
        <NavLink
          to="/admin/users"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )
          }
        >
          <Settings className="size-4" />
          Administration
        </NavLink>
      </div>
    </aside>
  );
}
