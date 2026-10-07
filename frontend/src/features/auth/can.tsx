import type { ReactNode } from "react";

import { useHasPermission } from "@/features/auth/use-permissions";
import type { Permission } from "@/types/auth";

type CanProps = {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
};

/**
 * UI-only permission gate. The backend always enforces authorization.
 */
export function Can({ permission, children, fallback = null }: CanProps) {
  return useHasPermission(permission) ? <>{children}</> : <>{fallback}</>;
}
