import { useMemo } from "react";

import { useCurrentUser } from "@/features/auth/use-current-user";
import type { Permission } from "@/types/auth";

export function usePermissions(): Set<string> {
  const { data: currentUser } = useCurrentUser();

  return useMemo(
    () => new Set(currentUser?.permissions ?? []),
    [currentUser],
  );
}

export function useHasPermission(permission: Permission): boolean {
  return usePermissions().has(permission);
}
