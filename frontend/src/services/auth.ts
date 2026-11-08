const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export type LoginRole = "STUDENT" | "ALUMNI" | "RECRUITER";

export interface AlumniRegistrationDetails {
  department: string;
  degree_programme: string;
  graduation_year: number;
  graduation_proof: File;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_verified: boolean;
}

interface TokenPair {
  access: string;
  refresh: string;
}

export class ApiError extends Error {
  public readonly payload: unknown;
  public readonly status: number;

  constructor(payload: unknown, status: number) {
    super(getApiErrorMessage(payload));
    this.name = "ApiError";
    this.payload = payload;
    this.status = status;
  }
}

const ACCESS_KEY = "nexus_access_token";
const REFRESH_KEY = "nexus_refresh_token";

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY);
}

function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(ACCESS_KEY, tokens.access);
  sessionStorage.setItem(REFRESH_KEY, tokens.refresh);
}

export function clearAuthTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function getApiErrorMessage(payload: unknown): string {
  if (payload instanceof Error) {
    return payload.message;
  }
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload === "object") {
    const data = payload as Record<string, unknown>;
    if (typeof data.detail === "string") {
      return data.detail;
    }
    return Object.entries(data)
      .map(([field, value]) => {
        const message = Array.isArray(value) ? value.join(", ") : String(value);
        return `${field}: ${message}`;
      })
      .join(" | ");
  }
  return "Something went wrong. Please try again.";
}

async function readResponse<T>(response: Response): Promise<T> {
  const data =
    response.status === 204 || response.status === 205
      ? null
      : await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(data, response.status);
  }
  return data as T;
}

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) {
    return false;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ refresh }),
    });
    if (!response.ok) {
      clearAuthTokens();
      return false;
    }
    const tokens = (await response.json()) as TokenPair;
    saveTokens(tokens);
    return true;
  } catch {
    clearAuthTokens();
    return false;
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
  retryOnUnauthorized = true
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      "Cannot connect to the backend. Check that Django is running on port 8000."
    );
  }

  if (response.status === 401 && token && retryOnUnauthorized) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest<T>(
        path,
        options,
        getAccessToken() ?? undefined,
        false
      );
    }
    clearAuthTokens();
  }
  return readResponse<T>(response);
}

export async function authenticatedRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();
  if (!token) {
    throw new Error("Please sign in to continue.");
  }
  return apiRequest<T>(path, options, token);
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const tokens = await apiRequest<TokenPair>("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  saveTokens(tokens);
  try {
    return await getCurrentUser();
  } catch (error) {
    clearAuthTokens();
    throw error;
  }
}

export async function register(
  username: string,
  email: string,
  password: string,
  role: LoginRole,
  alumniDetails?: AlumniRegistrationDetails
): Promise<AuthUser> {
  const formData = new FormData();
  formData.append("username", username);
  formData.append("email", email);
  formData.append("password", password);
  formData.append("role", role);

  if (role === "ALUMNI") {
    if (!alumniDetails) {
      throw new Error("Alumni registration requires graduation details and proof.");
    }
    formData.append("department", alumniDetails.department);
    formData.append("degree_programme", alumniDetails.degree_programme);
    formData.append("graduation_year", String(alumniDetails.graduation_year));
    formData.append("graduation_proof", alumniDetails.graduation_proof);
  }

  const createdUser = await apiRequest<AuthUser>("/auth/register/", {
    method: "POST",
    body: formData,
  });

  if (createdUser.role !== role) {
    throw new Error("The server created an account with an unexpected role. Please contact support.");
  }

  return login(username, password);
}

export async function getCurrentUser(): Promise<AuthUser> {
  if (!getAccessToken() && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) {
      throw new Error("Your session has expired. Please log in again.");
    }
  }
  const token = getAccessToken();
  if (!token) {
    throw new Error("You are not logged in.");
  }
  return apiRequest<AuthUser>("/auth/me/", {}, token);
}

export async function logout(): Promise<void> {
  const access = getAccessToken();
  const refresh = getRefreshToken();
  try {
    if (access && refresh) {
      await apiRequest(
        "/auth/logout/",
        {
          method: "POST",
          body: JSON.stringify({ refresh }),
        },
        access,
        false
      );
    }
  } catch {
    // Always clear the local session, even if the backend is unavailable.
  } finally {
    clearAuthTokens();
  }
}
