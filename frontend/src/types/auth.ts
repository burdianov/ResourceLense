export const PERMISSIONS = [
  "users.view",
  "users.create",
  "users.edit",
  "roles.view",
  "roles.create",
  "roles.edit",
  "roles.delete",
  "projects.view",
  "projects.create",
  "projects.edit",
  "projects.delete",
  "resources.view",
  "resources.create",
  "resources.edit",
  "resources.delete",
  "planning.view",
  "planning.edit",
  "reports.view",
] as const;

export type Permission = (typeof PERMISSIONS)[number];

export type CurrentUser = {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
  permissions: string[];
};

export type LoginCredentials = {
  email: string;
  password: string;
};
