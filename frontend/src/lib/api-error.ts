import { isAxiosError } from "axios";

type ValidationIssue = { msg?: unknown };

/**
 * Turn an API failure into a message worth showing the user.
 *
 * FastAPI returns `{"detail": "..."}` for raised HTTPExceptions and
 * `{"detail": [{"msg": "..."}]}` for request validation errors.
 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) {
    return fallback;
  }

  const data = error.response?.data as { detail?: unknown } | undefined;
  const detail = data?.detail;

  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const issue = detail[0] as ValidationIssue | undefined;

    if (issue && typeof issue.msg === "string") {
      return issue.msg;
    }
  }

  return fallback;
}
