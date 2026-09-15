import {
  canOnPlatform,
  PLATFORM_PERMISSIONS,
} from "../platform/platformAccess";
import type { MeResponse } from "./types";

/** Where a logged-in account lands, per HU-1: straight into the only firm it
 * belongs to, a picker when there is more than one, and an explanatory screen
 * when there is none. One function so the login screen and a page reload
 * resolve the exact same destination.
 *
 * Support is asked about first (HU-7). It belongs to no firm on purpose
 * (ADR-002 section 5), so without this it would land on "you do not belong to
 * any firm yet", which is the wrong message for the account that creates them. */
export function resolveHomePath(account: MeResponse): string {
  if (canOnPlatform(account, PLATFORM_PERMISSIONS.viewFirms)) {
    return "/platform/firms";
  }
  if (account.firms.length === 0) {
    return "/no-firm";
  }
  if (account.firms.length === 1) {
    return `/firms/${account.firms[0].id}/projects`;
  }
  return "/firms";
}
