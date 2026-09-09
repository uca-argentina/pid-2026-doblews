import type { MeResponse } from "./types";

/** Where a logged-in account lands, per HU-1: straight into the only firm it
 * belongs to, a picker when there is more than one, and an explanatory screen
 * when there is none. One function so the login screen and a page reload
 * resolve the exact same destination. */
export function resolveHomePath(account: MeResponse): string {
  if (account.firms.length === 0) {
    return "/no-firm";
  }
  if (account.firms.length === 1) {
    return `/firms/${account.firms[0].id}/projects`;
  }
  return "/firms";
}
