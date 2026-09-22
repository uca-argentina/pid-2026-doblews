import { createContext, useContext } from "react";
import type { FirmDetail } from "../auth/types";

export interface CurrentFirm {
  firm: FirmDetail;
  /** Whether the caller holds a firm permission here, e.g. can("member.add").
   *
   * The one question the UI asks before showing a section or a button — never
   * "what is my role?", per ADR-002: roles are data, permissions are what the
   * code checks. The backend asks it again on every request. */
  can: (permission: string) => boolean;
}

/** Provided by FirmLayout, which has already resolved the firm from the URL.
 *
 * A .ts file with no components on purpose: react-refresh can only hot-reload
 * files that export components alone, so the provider lives in FirmLayout. */
export const FirmContext = createContext<CurrentFirm | null>(null);

/** The firm in the URL, for any screen under /firms/:firmId.
 *
 * Never null inside those screens: FirmLayout renders them only once the firm
 * has loaded, and shows its own loader and "not found" otherwise. */
export function useCurrentFirm(): CurrentFirm {
  const context = useContext(FirmContext);
  if (!context) {
    throw new Error(
      "useCurrentFirm must be used inside a /firms/:firmId route",
    );
  }
  return context;
}
