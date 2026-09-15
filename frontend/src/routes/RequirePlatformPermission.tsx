import type { ReactNode } from "react";
import { Alert } from "@mantine/core";
import { useAuth } from "../features/auth/AuthContext";
import {
  canOnPlatform,
  type PlatformPermission,
} from "../features/platform/platformAccess";

interface RequirePlatformPermissionProps {
  /** The platform permission the screen demands, e.g. "firm.view". */
  code: PlatformPermission;
  children: ReactNode;
}

/** Gate for a support screen, for the person who types its URL directly.
 *
 * The platform counterpart of RequirePermission: an owner holds firm.view in
 * their own firm, and that is not firm.view on the platform, so an owner who
 * types /platform/firms gets this explanation instead of the screen. An
 * explanation rather than a redirect, for the same reason as there: being sent
 * somewhere else with no reason reads as a broken app.
 *
 * It hides a screen, it does not protect it: every /platform request demands
 * the same permission again on the backend. */
export function RequirePlatformPermission({
  code,
  children,
}: RequirePlatformPermissionProps) {
  const { account } = useAuth();

  if (!canOnPlatform(account, code)) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Esta sección la administra el soporte de la plataforma.
      </Alert>
    );
  }

  return <>{children}</>;
}
