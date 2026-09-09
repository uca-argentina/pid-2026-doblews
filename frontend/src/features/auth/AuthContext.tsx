import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { fetchMe, login as requestLogin } from "./authService";
import { getStoredToken, setStoredToken, setUnauthorizedHandler } from "../../lib/api";
import type { MeResponse } from "./types";

// "checking" covers the one round trip on app boot that resolves whether a
// stored token still means something. Splitting it from "anonymous" is what
// lets ProtectedRoute show a loader instead of bouncing to /login for an
// instant on every reload.
type AuthStatus = "checking" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  account: MeResponse | null;
  login: (email: string, password: string) => Promise<MeResponse>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Derived synchronously rather than inside the effect below: with no stored
  // token there is nothing to resolve, so "checking" would be a state the app
  // renders for one frame for nothing. It also keeps the effect free of a
  // synchronous setState, which cascades renders.
  const [status, setStatus] = useState<AuthStatus>(() =>
    getStoredToken() ? "checking" : "anonymous",
  );
  const [account, setAccount] = useState<MeResponse | null>(null);

  const clearSession = useCallback(() => {
    setStoredToken(null);
    setAccount(null);
    setStatus("anonymous");
  }, []);

  // Registered once so a 401 on *any* request — not only login — drops the
  // session immediately, per ADR-002 section 9.
  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  // Resolves a stored token on mount, which is what makes the session survive
  // a page reload (HU-1 acceptance criterion).
  useEffect(() => {
    if (!getStoredToken()) {
      return;
    }

    let cancelled = false;
    fetchMe()
      .then((me) => {
        if (cancelled) return;
        setAccount(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (cancelled) return;
        clearSession();
      });

    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const token = await requestLogin(email, password);
    setStoredToken(token);
    const me = await fetchMe();
    setAccount(me);
    setStatus("authenticated");
    return me;
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, account, login, logout: clearSession }),
    [status, account, login, clearSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return context;
}
