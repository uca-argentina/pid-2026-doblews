import { api } from "../../lib/api";
import type { FirmDetail } from "../auth/types";

/** The active firm and the caller's permissions in it. A firm the caller does
 * not belong to answers 404, exactly like one that does not exist (ADR-002
 * section 9), so the only error a page has to explain is "not found". */
export async function fetchFirm(firmId: number): Promise<FirmDetail> {
  const { data } = await api.get<FirmDetail>(`/firms/${firmId}`);
  return data;
}
