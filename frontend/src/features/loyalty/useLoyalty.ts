import { useQuery } from "@tanstack/react-query";
import { fetchLoyalty } from "./loyaltyService";

/** Under ["firm", firmId] like everything a firm screen reads.
 *
 * Receiving an order is what earns points, so the order mutations invalidate
 * this key too (see useRefresh in usePurchaseOrders): otherwise a delivery
 * registered in one tab would leave the level behind in another. */
export const loyaltyKeys = {
  all: (firmId: number) => ["firm", firmId, "loyalty"] as const,
};

export function useLoyalty(firmId: number) {
  return useQuery({
    queryKey: loyaltyKeys.all(firmId),
    queryFn: () => fetchLoyalty(firmId),
  });
}
