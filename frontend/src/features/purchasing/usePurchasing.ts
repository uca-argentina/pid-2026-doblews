import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import { supplierKeys } from "../suppliers/useSuppliers";
import {
  fetchMaterialComparison,
  fetchProjectPurchasing,
} from "./purchasingService";

/** The comparison of one material hangs below the firm's suppliers, so any
 * write to a supplier or a price (which invalidates that subtree) refreshes
 * it. A work's purchasing hangs below the work, like its budget, so a change
 * to the take-off refreshes it. */
export const purchasingKeys = {
  material: (firmId: number, resourceId: number, quantity: string) =>
    [...supplierKeys.all(firmId), "compare", resourceId, quantity] as const,
  project: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "purchasing"] as const,
};

/** One material compared at a quantity. Asks nothing until both are chosen.
 *
 * keepPreviousData so that typing a new quantity re-orders the list in place
 * instead of blanking it to a spinner for every keystroke that gets through. */
export function useMaterialComparison(
  firmId: number,
  resourceId: number | null,
  quantity: string | null,
) {
  return useQuery({
    queryKey: purchasingKeys.material(firmId, resourceId ?? 0, quantity ?? ""),
    queryFn: () => fetchMaterialComparison(firmId, resourceId!, quantity!),
    enabled: resourceId !== null && quantity !== null,
    placeholderData: keepPreviousData,
  });
}

/** Every material of a work, each at the quantity the work needs. */
export function useProjectPurchasing(firmId: number, projectId: number) {
  return useQuery({
    queryKey: purchasingKeys.project(firmId, projectId),
    queryFn: () => fetchProjectPurchasing(firmId, projectId),
  });
}
