import { Navigate, Outlet, useLocation } from "react-router-dom";

import { PageLoader } from "@/components/shared/page-loader";
import { useCurrentUser } from "@/features/auth/use-current-user";
import { useHasPermission } from "@/features/auth/use-permissions";
import type { Permission } from "@/types/auth";

export function ProtectedRoute() {
  const location = useLocation();
  const { data: currentUser, isPending } = useCurrentUser();

  if (isPending) {
    return <PageLoader />;
  }

  if (!currentUser) {
    return (
      <Navigate to="/login" replace state={{ from: location.pathname }} />
    );
  }

  return <Outlet />;
}

export function PermissionRoute({ permission }: { permission: Permission }) {
  const hasPermission = useHasPermission(permission);

  if (!hasPermission) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <p className="text-sm text-muted-foreground">
          You do not have permission to view this page.
        </p>
      </div>
    );
  }

  return <Outlet />;
}
