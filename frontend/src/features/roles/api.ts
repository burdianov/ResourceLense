import { api } from "@/api/client";
import type {
  CreateRoleInput,
  PermissionRecord,
  Role,
  UpdateRoleInput,
} from "@/types/role";

export async function fetchRoles(): Promise<Role[]> {
  const { data } = await api.get<Role[]>("/roles/");

  return data;
}

export async function fetchPermissionCatalogue(): Promise<
  PermissionRecord[]
> {
  const { data } = await api.get<PermissionRecord[]>("/permissions/");

  return data;
}

export async function createRole(input: CreateRoleInput): Promise<Role> {
  const { data } = await api.post<Role>("/roles/", input);

  return data;
}

export async function updateRole(
  roleId: number,
  input: UpdateRoleInput,
): Promise<Role> {
  const { data } = await api.patch<Role>(`/roles/${roleId}`, input);

  return data;
}

export async function deleteRole(roleId: number): Promise<void> {
  await api.delete(`/roles/${roleId}`);
}
