import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
} from "@/features/users/api";
import { rolesQueryKey, usersQueryKey } from "@/lib/query-keys";
import type { UpdateUserInput } from "@/types/user";

export function useUsers() {
  return useQuery({
    queryKey: usersQueryKey,
    queryFn: fetchUsers,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: usersQueryKey });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      userId,
      input,
    }: {
      userId: number;
      input: UpdateUserInput;
    }) => updateUser(userId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: usersQueryKey });

      // Role assignments change the user counts shown on the roles screen.
      queryClient.invalidateQueries({ queryKey: rolesQueryKey });
    },
  });
}

export function useResetUserPassword() {
  return useMutation({
    mutationFn: ({
      userId,
      password,
    }: {
      userId: number;
      password: string;
    }) => resetUserPassword(userId, password),
  });
}
