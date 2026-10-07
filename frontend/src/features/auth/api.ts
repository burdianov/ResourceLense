import { api } from "@/api/client";
import type { CurrentUser, LoginCredentials } from "@/types/auth";

export async function login(credentials: LoginCredentials): Promise<void> {
  await api.post("/auth/login", credentials);
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const { data } = await api.get<CurrentUser>("/auth/me");

  return data;
}
