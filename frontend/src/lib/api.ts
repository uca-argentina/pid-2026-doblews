import axios from "axios";

// Single key for the access token, per ADR-004: no refresh token, no other
// session data lives in the browser.
const TOKEN_STORAGE_KEY = "warchitecture.token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Attaches the bearer token to every request. Reading it from storage instead
// of from React state means this file has no dependency on the auth context,
// which is what lets AuthProvider import this module instead of the other way
// around.
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// AuthProvider registers itself here so that a 401 from *any* authenticated
// request (not just login) clears the session immediately, matching ADR-002
// section 9: a revoked account must stop working on its very next request.
let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      unauthorizedHandler?.();
    }
    return Promise.reject(error);
  },
);
