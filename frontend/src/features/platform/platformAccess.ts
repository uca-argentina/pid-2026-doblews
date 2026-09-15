import type { MeResponse } from "../auth/types";

/** The platform permissions the support screens ask about. Spelled once, so a
 * typo is a compile error instead of a section that silently never shows. */
export const PLATFORM_PERMISSIONS = {
  viewFirms: "firm.view",
  createFirm: "firm.create",
  suspendFirm: "firm.suspend",
  resetPassword: "account.reset_password",
} as const;

export type PlatformPermission =
  (typeof PLATFORM_PERMISSIONS)[keyof typeof PLATFORM_PERMISSIONS];

/** Whether the logged-in account holds a platform permission.
 *
 * The platform counterpart of useCurrentFirm().can(): the same question —
 * never "is this support?" — asked of /auth/me instead of GET /firms/{id},
 * because platform permissions depend on the account and not on a firm. */
export function canOnPlatform(
  account: MeResponse | null,
  permission: PlatformPermission,
): boolean {
  return account?.platform_permissions.includes(permission) ?? false;
}
