import { api } from "../../lib/api";
import type { BudgetOut } from "./types";

/** The one call HU-11's screen makes. The budget is derived from the take-off,
 * so there is nothing to write here: HU-5's line endpoints are what change it. */
export async function fetchBudget(
  firmId: number,
  projectId: number,
): Promise<BudgetOut> {
  const { data } = await api.get<BudgetOut>(
    `/firms/${firmId}/projects/${projectId}/budget`,
  );
  return data;
}
