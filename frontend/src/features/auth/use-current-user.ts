import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCurrentUser, login, logout } from "@/features/auth/api";
import { currentUserQueryKey } from "@/lib/query-keys";
import type { CurrentUser } from "@/types/auth";

/**
 * The single source of truth for the signed-in user.
 *
 * `data === null` means we know the visitor is signed out (e.g. straight
 * after logout or when the API answered 401). `data === undefined` while
 * `isPending` means we do not know yet. The backend always enforces
 * authorisation; this only drives the UI.
 */
export function useCurrentUser() {
  return useQuery<CurrentUser | null>({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: login,
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: currentUserQueryKey });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSuccess: () => {
      // Drop every cached response: the next person to sign in on this
      // browser must not be able to read the previous user's data.
      queryClient.clear();
      queryClient.setQueryData<CurrentUser | null>(currentUserQueryKey, null);
    },
  });
}
