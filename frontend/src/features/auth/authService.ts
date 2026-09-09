import { api } from "../../lib/api";
import type { MeResponse, TokenResponse } from "./types";

/** Exchanges credentials for an access token. Does not store it: the caller
 * decides when the session actually starts, so this stays a pure API call. */
export async function login(email: string, password: string): Promise<string> {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
  return data.access_token;
}

/** The session as the backend sees it: who I am and which firms I can act in.
 * Called both right after login and on every app boot with a stored token, so
 * a bug here shows up in one code path instead of hiding in a duplicate. */
export async function fetchMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>("/auth/me");
  return data;
}
