import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

import { API_URL } from "@/lib/config";
import type { ErrorCode, ErrorData, QuotationRead, VersionConflictData } from "@/lib/api/types";
import type { UserType } from "@/lib/types";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  user_type: UserType;
}

/** Envelope every backend endpoint responds with. */
interface Envelope<T> {
  success: boolean;
  message: string;
  data: T;
}

export const tokenStorage = {
  getAccess: () =>
    typeof window === "undefined" ? null : localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () =>
    typeof window === "undefined" ? null : localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (tokens: TokenPair) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export const apiClient = axios.create({ baseURL: API_URL });

apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Every request carries its own request id, echoed back by the backend on
  // error responses (`data.request_id`) — grep this alongside a failure in the
  // UI to find the matching backend log line. Contract §1.
  config.headers["X-Request-ID"] = crypto.randomUUID();
  return config;
});

// Unwrap the {success, message, data} envelope so callers just deal with `data`.
apiClient.interceptors.response.use((response) => {
  response.data = (response.data as Envelope<unknown>).data;
  return response;
});

// Deduplicates concurrent refresh attempts
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefresh();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post<Envelope<TokenPair>>(`${API_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    tokenStorage.set(data.data);
    return data.data.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableConfig | undefined;
    const isAuthEndpoint =
      original?.url?.includes("/auth/login") || original?.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const token = await refreshPromise;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return apiClient(original);
      }
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

/** Extract a human-readable message from any error (backend envelope aware). */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as Envelope<unknown> | undefined;
    if (body?.message) return body.message;
    return error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong";
}

// ---------------------------------------------------------------------------------
// Typed API errors — `API_CONTRACT.md` §1 "Error envelope". On a non-2xx response,
// `data.code` (nested inside the app's `{success, message, data}` envelope, not a
// flat `ApiError`) discriminates the failure. Callers should catch these typed
// classes instead of poking at `error.response.data` themselves.
// ---------------------------------------------------------------------------------

export class ApiError extends Error {
  code: ErrorCode | null;
  requestId: string;
  status: number;
  data: ErrorData;

  constructor(message: string, data: ErrorData, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = data.code;
    this.requestId = data.request_id;
    this.status = status;
    this.data = data;
  }
}

/** `409 VERSION_CONFLICT` — carries the server's current truth so the caller
 * never needs a follow-up GET. Contract §7. */
export class VersionConflictError extends ApiError {
  current: QuotationRead;
  currentVersion: number;

  constructor(message: string, data: VersionConflictData, status: number) {
    super(message, data, status);
    this.name = "VersionConflictError";
    this.current = data.current;
    this.currentVersion = data.current_version;
  }
}

export class IllegalTransitionError extends ApiError {
  constructor(message: string, data: ErrorData, status: number) {
    super(message, data, status);
    this.name = "IllegalTransitionError";
  }
}

export class InsufficientStockError extends ApiError {
  constructor(message: string, data: ErrorData, status: number) {
    super(message, data, status);
    this.name = "InsufficientStockError";
  }
}

export class PolicyViolationError extends ApiError {
  constructor(message: string, data: ErrorData, status: number) {
    super(message, data, status);
    this.name = "PolicyViolationError";
  }
}

/** `403 FORBIDDEN_PRINCIPAL` or `403 PERMISSION_DENIED`. */
export class PermissionError extends ApiError {
  constructor(message: string, data: ErrorData, status: number) {
    super(message, data, status);
    this.name = "PermissionError";
  }
}

function hasErrorCode(value: unknown): value is ErrorData {
  return typeof value === "object" && value !== null && "code" in value && "request_id" in value;
}

// Runs after the refresh-on-401 interceptor above, so it sees the final
// rejection (a failed refresh, or any other non-2xx) and upgrades it to a
// typed error before it reaches calling code.
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const body = error.response?.data as Envelope<unknown> | undefined;

    if (status && body && hasErrorCode(body.data)) {
      const data = body.data;
      const message = body.message;
      switch (data.code) {
        case "VERSION_CONFLICT":
          return Promise.reject(
            new VersionConflictError(message, data as VersionConflictData, status)
          );
        case "ILLEGAL_TRANSITION":
          return Promise.reject(new IllegalTransitionError(message, data, status));
        case "INSUFFICIENT_STOCK":
          return Promise.reject(new InsufficientStockError(message, data, status));
        case "POLICY_VIOLATION":
          return Promise.reject(new PolicyViolationError(message, data, status));
        case "FORBIDDEN_PRINCIPAL":
        case "PERMISSION_DENIED":
          return Promise.reject(new PermissionError(message, data, status));
        default:
          break;
      }
    }
    return Promise.reject(error);
  }
);
