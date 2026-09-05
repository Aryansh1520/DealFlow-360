/**
 * Converts a `MockApiError` into the exact same typed error class the real
 * Axios interceptor produces (`src/lib-api-client.ts`) — so calling code
 * (hooks, components) never has to know whether it's talking to the mock
 * store or the real backend. Swapping `USE_MOCKS` off is a no-op for every
 * consumer of these errors.
 */
import {
  ApiError,
  IllegalTransitionError,
  PolicyViolationError,
  VersionConflictError,
} from "@/lib/api-client";
import { MockApiError } from "@/lib/api/mock/store";
import type { ErrorData, VersionConflictData } from "@/lib/api/types";

export function toApiError(error: unknown): never {
  if (!(error instanceof MockApiError)) throw error;

  const data: ErrorData = { code: error.code as ErrorData["code"], request_id: "mock", ...error.extra };

  switch (error.code) {
    case "VERSION_CONFLICT":
      throw new VersionConflictError(error.message, data as VersionConflictData, error.status);
    case "ILLEGAL_TRANSITION":
      throw new IllegalTransitionError(error.message, data, error.status);
    case "POLICY_VIOLATION":
      throw new PolicyViolationError(error.message, data, error.status);
    default:
      throw new ApiError(error.message, data, error.status);
  }
}
