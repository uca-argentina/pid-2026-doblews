import { Center, Loader } from "@mantine/core";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { resolveHomePath } from "../features/auth/navigation";

/** Keeps a logged-in account off the login screen: hitting /login while
 * authenticated sends it to wherever it already belongs instead of showing
 * the form again. */
export function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { status, account } = useAuth();

  if (status === "checking") {
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  }

  if (status === "authenticated" && account) {
    return <Navigate to={resolveHomePath(account)} replace />;
  }

  return <>{children}</>;
}
