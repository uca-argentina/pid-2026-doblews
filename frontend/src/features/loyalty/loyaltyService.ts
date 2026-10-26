import { api } from "../../lib/api";
import type { LoyaltyOut } from "./types";

/** The firm's level and the entries behind it (HU-24, ADR-012 section 7).
 *
 * One request for the whole screen: the history comes whole and unpaged, like
 * the firm's order listing, because a studio's received orders are few. The
 * level with each supplier does not live here — it travels in that supplier's
 * own detail, so its card costs no extra request. */
export async function fetchLoyalty(firmId: number): Promise<LoyaltyOut> {
  const { data } = await api.get<LoyaltyOut>(`/firms/${firmId}/loyalty`);
  return data;
}
