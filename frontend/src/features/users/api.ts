import { api } from "@/api/client";
import type {
  CreateUserInput,
  UpdateUserInput,
  UserSummary,
} from "@/types/user";

export async function fetchUsers(): Promise<UserSummary[]> {
  const { data } = await api.get<UserSummary[]>("/users/");

  return data;
}

export async function createUser(
  input: CreateUserInput,
): Promise<UserSummary> {
  const { data } = await api.post<UserSummary>("/users/", input);

  return data;
}

export async function updateUser(
  userId: number,
  input: UpdateUserInput,
): Promise<UserSummary> {
  const { data } = await api.patch<UserSummary>(`/users/${userId}`, input);

  return data;
}

export async function resetUserPassword(
  userId: number,
  password: string,
): Promise<void> {
  await api.put(`/users/${userId}/password`, { password });
}
