export type UserSummary = {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
};

export type CreateUserInput = {
  email: string;
  full_name: string;
  password: string;
  roles: string[];
};

export type UpdateUserInput = {
  full_name?: string;
  is_active?: boolean;
  roles?: string[];
};
