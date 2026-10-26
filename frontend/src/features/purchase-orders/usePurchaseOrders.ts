import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import {
  addLine,
  cancelOrder,
  changeLineSupplier,
  deactivateLine,
  deactivateReceipt,
  discardOrder,
  fetchFirmOrders,
  fetchOrder,
  fetchProjectOrders,
  generateOrders,
  issueOrder,
  registerReceipt,
  updateLine,
} from "./purchaseOrderService";
import type { GenerateItem, OrderStatus, ReceiptIn } from "./types";

/** Query keys for a firm's orders, under ["firm", firmId] like everything a
 * firm screen reads, so one invalidation of `all` refreshes every listing and
 * every open order. */
export const purchaseOrderKeys = {
  all: (firmId: number) => ["firm", firmId, "purchase-orders"] as const,
  detail: (firmId: number, orderId: number) =>
    [...purchaseOrderKeys.all(firmId), orderId] as const,
  project: (firmId: number, projectId: number, status?: OrderStatus) =>
    [...purchaseOrderKeys.all(firmId), "project", projectId, status] as const,
  firm: (firmId: number) => [...purchaseOrderKeys.all(firmId), "list"] as const,
};

export function useFirmOrders(firmId: number) {
  return useQuery({
    queryKey: purchaseOrderKeys.firm(firmId),
    queryFn: () => fetchFirmOrders(firmId),
  });
}

export function useProjectOrders(
  firmId: number,
  projectId: number,
  status?: OrderStatus,
) {
  return useQuery({
    queryKey: purchaseOrderKeys.project(firmId, projectId, status),
    queryFn: () => fetchProjectOrders(firmId, projectId, status),
  });
}

/** retry: false, as with a supplier: the 404 to expect (another firm's order,
 * a discarded draft) will not change by asking again. */
export function useOrder(firmId: number, orderId: number) {
  return useQuery({
    queryKey: purchaseOrderKeys.detail(firmId, orderId),
    queryFn: () => fetchOrder(firmId, orderId),
    retry: false,
  });
}

/** Every write refreshes the firm's orders and the firm's works: the latter
 * holds each work's comparison, whose "ya pedido" follows the drafts. Returning
 * the invalidation keeps the mutation pending until the refetch is done, so a
 * modal closes onto a screen that already shows the change. */
function useRefresh(firmId: number) {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: purchaseOrderKeys.all(firmId),
      }),
      queryClient.invalidateQueries({ queryKey: projectKeys.all(firmId) }),
    ]);
}

export function useGenerateOrders(firmId: number, projectId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (items: GenerateItem[]) =>
      generateOrders(firmId, projectId, items),
    onSuccess: refresh,
  });
}

export function useAddLine(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (payload: { resource_id: number; quantity: string }) =>
      addLine(firmId, orderId, payload),
    onSuccess: refresh,
  });
}

export function useUpdateLine(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (variables: { lineId: number; quantity: string }) =>
      updateLine(firmId, orderId, variables.lineId, variables.quantity),
    onSuccess: refresh,
  });
}

export function useChangeLineSupplier(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (variables: { lineId: number; supplierId: number }) =>
      changeLineSupplier(
        firmId,
        orderId,
        variables.lineId,
        variables.supplierId,
      ),
    onSuccess: refresh,
  });
}

export function useDeactivateLine(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (lineId: number) => deactivateLine(firmId, orderId, lineId),
    onSuccess: refresh,
  });
}

export function useDiscardOrder(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (orderId: number) => discardOrder(firmId, orderId),
    onSuccess: refresh,
  });
}

export function useIssueOrder(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (orderId: number) => issueOrder(firmId, orderId),
    onSuccess: refresh,
  });
}

export function useCancelOrder(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (orderId: number) => cancelOrder(firmId, orderId),
    onSuccess: refresh,
  });
}

export function useRegisterReceipt(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (payload: ReceiptIn) =>
      registerReceipt(firmId, orderId, payload),
    onSuccess: refresh,
  });
}

export function useDeactivateReceipt(firmId: number, orderId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (receiptId: number) =>
      deactivateReceipt(firmId, orderId, receiptId),
    onSuccess: refresh,
  });
}
