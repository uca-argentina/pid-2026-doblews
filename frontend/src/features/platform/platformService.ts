import { api } from "../../lib/api";
import type {
  FirmAdminOut,
  FirmCreate,
  FirmCreatedOut,
  FirmStatusUpdate,
  PasswordReset,
} from "./types";

/** Every call the support screens make. One module so the URLs live in one
 * place, and the hooks in usePlatform.ts stay about caching.
 *
 * Nothing here hangs off /firms/{id}: support belongs to no roster, so it acts
 * on firms from /platform (ADR-002 section 10.1). */

const FIRMS_URL = "/platform/firms";

/** Every firm on the platform, suspended ones included: the listing is where
 * support finds a firm to reactivate. */
export async function fetchPlatformFirms(): Promise<FirmAdminOut[]> {
  const { data } = await api.get<FirmAdminOut[]>(FIRMS_URL);
  return data;
}

/** Creates a firm together with its owner. The owner comes back as stored, so
 * the caller can tell whether the typed name was kept. */
export async function createFirm(payload: FirmCreate): Promise<FirmCreatedOut> {
  const { data } = await api.post<FirmCreatedOut>(FIRMS_URL, payload);
  return data;
}

/** Suspends (is_active: false) or reactivates a firm. Nothing is deleted. */
export async function changeFirmStatus(
  firmId: number,
  payload: FirmStatusUpdate,
): Promise<FirmAdminOut> {
  const { data } = await api.patch<FirmAdminOut>(
    `${FIRMS_URL}/${firmId}`,
    payload,
  );
  return data;
}

/** Gives an account a new password, found by its email. 204 with no body. The
 * email travels in the body and never in the URL, where it would be logged. */
export async function resetPassword(payload: PasswordReset): Promise<void> {
  await api.put("/platform/accounts/password", payload);
}
