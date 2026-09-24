/**
 * Auth utility functions for JWT token management.
 *
 * Stores the JWT token and user info in localStorage.
 * Used by all components that need to make authenticated API calls.
 */

const TOKEN_KEY = "nexus_auth_token";
const USER_KEY = "nexus_auth_user";

export interface AuthUser {
  id: number;
  username: string;
}

/**
 * Get the stored JWT token, or null if not authenticated.
 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store the JWT token.
 */
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Get the stored user info, or null if not authenticated.
 */
export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

/**
 * Store user info alongside the token.
 */
export function setUser(user: AuthUser): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/**
 * Clear all auth data (logout).
 */
export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Check if the user is currently authenticated.
 * Does not validate token expiry — the backend will reject expired tokens.
 */
export function isAuthenticated(): boolean {
  return !!getToken() && !!getUser();
}

/**
 * Perform login API call.
 * Returns { token, user } on success, throws on failure.
 */
export async function loginUser(
  username: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch("http://localhost:8000/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Login failed (HTTP ${res.status})`);
  }

  const data = await res.json();
  setToken(data.token);
  setUser(data.user);
  return data;
}

/**
 * Perform registration API call.
 * Returns { token, user } on success, throws on failure.
 */
export async function registerUser(
  username: string,
  password: string
): Promise<{ token: string; user: AuthUser }> {
  const res = await fetch("http://localhost:8000/api/v1/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Registration failed (HTTP ${res.status})`);
  }

  const data = await res.json();
  setToken(data.token);
  setUser(data.user);
  return data;
}
