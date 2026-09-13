import type { ReactNode } from "react";
import { Alert } from "@mantine/core";
import { useCurrentFirm } from "../features/firms/firmContext";

interface RequirePermissionProps {
  /** The firm permission the screen demands, e.g. "member.add". */
  code: string;
  /** Why the section is closed, in the section's own terms. Defaults to the
   * roster's explanation, which was the first screen gated here. */
  message?: string;
  children: ReactNode;
}

/** Gate for a section inside a firm, for the person who types its URL directly.
 *
 * This is HU-2's "un architect entra por URL directa y recibe 403": the link is
 * already hidden from the sidebar, and this is what answers when someone gets
 * there anyway. An explanation rather than a redirect, because being sent
 * somewhere else with no reason reads as a broken app.
 *
 * It hides a screen, it does not protect it: the data behind it is protected by
 * the backend, which demands the same permission on every request. A firm that
 * is not the caller's never gets this far — FirmLayout has already answered it
 * with "not found", so nothing here confirms that a foreign firm exists. */
export function RequirePermission({
  code,
  message = "Esta sección la administra el propietario del estudio.",
  children,
}: RequirePermissionProps) {
  const { can } = useCurrentFirm();

  if (!can(code)) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        {message}
      </Alert>
    );
  }

  return <>{children}</>;
}
