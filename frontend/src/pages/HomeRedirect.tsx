import { Navigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { resolveHomePath } from "../features/auth/navigation";

/** Sits behind ProtectedRoute, so `account` is always set by the time this
 * renders. Exists so "/" has one destination, computed the same way whether
 * you land here right after login or from a bookmark. */
export function HomeRedirect() {
  const { account } = useAuth();

  if (!account) {
    return null;
  }

  return <Navigate to={resolveHomePath(account)} replace />;
}
