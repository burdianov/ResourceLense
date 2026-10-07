import type { QueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import { api } from "@/api/client";
import { currentUserQueryKey } from "@/lib/query-keys";
import type { CurrentUser } from "@/types/auth";

/**
 * Treat an expired or revoked session as a signed-out state.
 *
 * Clearing the cached user makes `ProtectedRoute` redirect to /login, and
 * navigates back to the originally requested page after signing in again.
 */
export function setupApiInterceptors(queryClient: QueryClient) {
  api.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      if (isAxiosError(error) && error.response?.status === 401) {
        const url = error.config?.url ?? "";

        // A 401 from the login endpoint means bad credentials, not an
        // expired session, so it must not clear the current user.
        if (!url.includes("/auth/login")) {
          queryClient.setQueryData<CurrentUser | null>(
            currentUserQueryKey,
            null,
          );
        }
      }

      return Promise.reject(error);
    },
  );
}
