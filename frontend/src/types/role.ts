export type Role = {
  id: number;
  name: string;
  description: string | null;
  permissions: string[];
  user_count: number;
  is_protected: boolean;
};

export type PermissionRecord = {
  id: number;
  name: string;
  description: string | null;
};

export type CreateRoleInput = {
  name: string;
  description: string | null;
  permissions: string[];
};

export type UpdateRoleInput = {
  name?: string;
  description?: string | null;
  permissions?: string[];
};
