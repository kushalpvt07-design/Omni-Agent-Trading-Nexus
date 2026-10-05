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
 * Decode the JWT payload without verifying the signature.
 * Used solely to read the `exp` claim client-side.
 * Signature verification is always done server-side.
 */
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    // JWT base64url → standard base64
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(base64);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Returns true if the stored JWT token is expired or unreadable.
 * A 30-second buffer is applied so tokens near expiry are treated as expired.
 */
export function isTokenExpired(): boolean {
  const token = getToken();
  if (!token) return true;
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return true;
  // exp is in seconds; Date.now() is in ms. Add a 30s safety buffer.
  return payload.exp * 1000 < Date.now() + 30_000;
}

/**
 * Check if the user is currently authenticated with a non-expired token.
 * Clears stale localStorage data when the token has expired so the user
 * is redirected to login rather than hitting a wall of 401/403 errors.
 */
export function isAuthenticated(): boolean {
  if (!getToken() || !getUser()) return false;
  if (isTokenExpired()) {
    // Purge expired session so page.tsx redirects to /login immediately.
    clearAuth();
    return false;
  }
  return true;
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
