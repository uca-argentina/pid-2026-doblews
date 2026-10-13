import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addPrice,
  createSupplier,
  deactivateSupplier,
  fetchSupplier,
  fetchSuppliers,
  removePrice,
  updatePrice,
  updateSupplier,
} from "./supplierService";
import type {
  SupplierPriceCreate,
  SupplierPriceUpdate,
  SupplierWrite,
} from "./types";

/** Query keys for a firm's suppliers, under ["firm", firmId] like everything
 * else a firm screen reads. The detail key starts with the list's, so one
 * invalidation of `all` refreshes both the listing and any open list. */
export const supplierKeys = {
  all: (firmId: number) => ["firm", firmId, "suppliers"] as const,
  detail: (firmId: number, supplierId: number) =>
    ["firm", firmId, "suppliers", supplierId] as const,
};

/** The firm's suppliers. */
export function useSuppliers(firmId: number) {
  return useQuery({
    queryKey: supplierKeys.all(firmId),
    queryFn: () => fetchSuppliers(firmId),
  });
}

/** One supplier with its price list.
 *
 * retry: false because the 404 to expect (another firm's supplier, or one that
 * was given up) will not change by asking again, and the screen shows its own
 * "not found" instead of a spinner for three attempts. */
export function useSupplier(firmId: number, supplierId: number) {
  return useQuery({
    queryKey: supplierKeys.detail(firmId, supplierId),
    queryFn: () => fetchSupplier(firmId, supplierId),
    retry: false,
  });
}

/** Every write refreshes the firm's suppliers, listing and lists alike.
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the refetch is done, so a modal closes onto a screen that already shows the
 * change. Errors are rendered by each modal, next to the form. */
function useRefresh(firmId: number) {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: supplierKeys.all(firmId) });
}

export function useCreateSupplier(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (payload: SupplierWrite) => createSupplier(firmId, payload),
    onSuccess: refresh,
  });
}

export function useUpdateSupplier(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (variables: { supplierId: number; payload: SupplierWrite }) =>
      updateSupplier(firmId, variables.supplierId, variables.payload),
    onSuccess: refresh,
  });
}

export function useDeactivateSupplier(firmId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (supplierId: number) => deactivateSupplier(firmId, supplierId),
    onSuccess: refresh,
  });
}

export function useAddPrice(firmId: number, supplierId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (payload: SupplierPriceCreate) =>
      addPrice(firmId, supplierId, payload),
    onSuccess: refresh,
  });
}

export function useUpdatePrice(firmId: number, supplierId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (variables: {
      priceId: number;
      payload: SupplierPriceUpdate;
    }) => updatePrice(firmId, supplierId, variables.priceId, variables.payload),
    onSuccess: refresh,
  });
}

export function useRemovePrice(firmId: number, supplierId: number) {
  const refresh = useRefresh(firmId);
  return useMutation({
    mutationFn: (priceId: number) => removePrice(firmId, supplierId, priceId),
    onSuccess: refresh,
  });
}
