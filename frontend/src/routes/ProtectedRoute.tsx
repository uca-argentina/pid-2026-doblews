import { Center, Loader } from "@mantine/core";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

/** Gate for every screen that needs a session. Redirects anonymous visitors to
 * /login and remembers where they were headed, so a link straight to a
 * project can send them back there once they log in. */
export function ProtectedRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
