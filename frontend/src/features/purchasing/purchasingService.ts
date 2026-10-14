import { api } from "../../lib/api";
import type { MaterialComparisonOut, ProjectPurchasingOut } from "./types";

/** The two reads of HU-18. Nothing is written: the comparison is computed on
 * every read and no choice of supplier is ever recorded (ADR-010 section 4). */

/** Every offer the firm has for one material, cheapest first, for a quantity
 * (a decimal string, as the API takes it). */
export async function fetchMaterialComparison(
  firmId: number,
  resourceId: number,
  quantity: string,
): Promise<MaterialComparisonOut> {
  const { data } = await api.get<MaterialComparisonOut>(
    `/firms/${firmId}/purchasing/compare`,
    { params: { resource_id: resourceId, quantity } },
  );
  return data;
}

/** Each material of a work's take-off, with every offer for its quantity. */
export async function fetchProjectPurchasing(
  firmId: number,
  projectId: number,
): Promise<ProjectPurchasingOut> {
  const { data } = await api.get<ProjectPurchasingOut>(
    `/firms/${firmId}/projects/${projectId}/purchasing`,
  );
  return data;
}
