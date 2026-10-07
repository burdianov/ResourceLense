import {
  BarChart3,
  BriefcaseBusiness,
  LayoutDashboard,
  ShieldCheck,
  UsersRound,
} from "lucide-react";

import { usePermissions } from "@/features/auth/use-permissions";
import type { Permission } from "@/types/auth";

export type NavItem = {
  name: string;
  href: string;
  icon: typeof LayoutDashboard;
  permission?: Permission;
};

export const primaryNavigation: NavItem[] = [
  {
    name: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Planning",
    href: "/planning",
    icon: BarChart3,
    permission: "planning.view",
  },
  {
    name: "Projects",
    href: "/projects",
    icon: BriefcaseBusiness,
    permission: "projects.view",
  },
  {
    name: "Resources",
    href: "/resources",
    icon: UsersRound,
    permission: "resources.view",
  },
  {
    name: "Reports",
    href: "/reports",
    icon: BarChart3,
    permission: "reports.view",
  },
];

export const administrationNavigation: NavItem[] = [
  {
    name: "Users",
    href: "/admin/users",
    icon: UsersRound,
    permission: "users.view",
  },
  {
    name: "Roles",
    href: "/admin/roles",
    icon: ShieldCheck,
    permission: "roles.view",
  },
];

export function useVisibleNavigation() {
  const permissions = usePermissions();

  function canSee(item: NavItem) {
    return !item.permission || permissions.has(item.permission);
  }

  return {
    primary: primaryNavigation.filter(canSee),
    administration: administrationNavigation.filter(canSee),
  };
}
