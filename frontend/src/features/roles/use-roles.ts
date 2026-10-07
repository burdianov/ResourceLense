import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createRole,
  deleteRole,
  fetchPermissionCatalogue,
  fetchRoles,
  updateRole,
} from "@/features/roles/api";
import {
  permissionCatalogueQueryKey,
  rolesQueryKey,
  usersQueryKey,
} from "@/lib/query-keys";
import type { UpdateRoleInput } from "@/types/role";

export function useRoles() {
  return useQuery({
    queryKey: rolesQueryKey,
    queryFn: fetchRoles,
  });
}

export function usePermissionCatalogue() {
  return useQuery({
    queryKey: permissionCatalogueQueryKey,
    queryFn: fetchPermissionCatalogue,
    staleTime: 5 * 60_000,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createRole,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rolesQueryKey });
    },
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      roleId,
      input,
    }: {
      roleId: number;
      input: UpdateRoleInput;
    }) => updateRole(roleId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rolesQueryKey });

      // Renaming a role changes the badges shown on the users screen.
      queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteRole,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rolesQueryKey });
      queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}
