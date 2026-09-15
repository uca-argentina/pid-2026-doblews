import { useAuth } from "../features/auth/AuthContext";
import { AppShellLayout } from "./AppShellLayout";
import { PlatformNavbar } from "./PlatformNavbar";

/** Everything under /platform: the shell with support's sidebar.
 *
 * Unlike FirmLayout there is nothing to fetch first. The platform is not a
 * resource in the URL that might not be yours; what the caller may do here is
 * already in /auth/me, which the session loaded before any route rendered.
 *
 * Someone with no platform permission at all — an owner typing the URL — gets
 * the shell without a sidebar, because there is no section to offer, and each
 * screen's RequirePlatformPermission explains why. */
export function PlatformLayout() {
  const { account } = useAuth();
  const hasAny = (account?.platform_permissions.length ?? 0) > 0;

  return (
    <AppShellLayout
      navbar={
        hasAny ? (close) => <PlatformNavbar onNavigate={close} /> : undefined
      }
    />
  );
}
