import { useQuery } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import { fetchBudget } from "./budgetService";

/** The budget hangs below its work's key, like the take-off, so a write to a
 * line — which invalidates that subtree — refetches this too. That is what
 * "se recalcula solo" means in practice: there is no budget cache of its own
 * to go stale behind the take-off's. */
export const budgetKeys = {
  one: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "budget"] as const,
};

/** The estimated budget of one work: the three groups and their totals. */
export function useBudget(firmId: number, projectId: number) {
  return useQuery({
    queryKey: budgetKeys.one(firmId, projectId),
    queryFn: () => fetchBudget(firmId, projectId),
  });
}
