import { api } from "../../lib/api";
import type {
  SupplierDetailOut,
  SupplierOut,
  SupplierPriceCreate,
  SupplierPriceOut,
  SupplierPriceUpdate,
  SupplierWrite,
} from "./types";

/** Every call the suppliers screens make, one module so the URLs live in one
 * place and the hooks in useSuppliers.ts stay about caching. All under the
 * firm: suppliers and their prices belong to it (ADR-010 section 1). */

function suppliersUrl(firmId: number): string {
  return `/firms/${firmId}/suppliers`;
}

/** The firm's live suppliers, by name, each with the length of its list. */
export async function fetchSuppliers(firmId: number): Promise<SupplierOut[]> {
  const { data } = await api.get<SupplierOut[]>(suppliersUrl(firmId));
  return data;
}

/** One supplier with its price list. A 404 covers another firm's supplier and
 * a deactivated one alike. */
export async function fetchSupplier(
  firmId: number,
  supplierId: number,
): Promise<SupplierDetailOut> {
  const { data } = await api.get<SupplierDetailOut>(
    `${suppliersUrl(firmId)}/${supplierId}`,
  );
  return data;
}

export async function createSupplier(
  firmId: number,
  payload: SupplierWrite,
): Promise<SupplierOut> {
  const { data } = await api.post<SupplierOut>(suppliersUrl(firmId), payload);
  return data;
}

export async function updateSupplier(
  firmId: number,
  supplierId: number,
  payload: SupplierWrite,
): Promise<SupplierOut> {
  const { data } = await api.patch<SupplierOut>(
    `${suppliersUrl(firmId)}/${supplierId}`,
    payload,
  );
  return data;
}

/** A logical removal, with the supplier's whole list. A POST and not a DELETE:
 * nothing is erased. 204 with no body. */
export async function deactivateSupplier(
  firmId: number,
  supplierId: number,
): Promise<void> {
  await api.post(`${suppliersUrl(firmId)}/${supplierId}/deactivate`);
}

export async function addPrice(
  firmId: number,
  supplierId: number,
  payload: SupplierPriceCreate,
): Promise<SupplierPriceOut> {
  const { data } = await api.post<SupplierPriceOut>(
    `${suppliersUrl(firmId)}/${supplierId}/prices`,
    payload,
  );
  return data;
}

export async function updatePrice(
  firmId: number,
  supplierId: number,
  priceId: number,
  payload: SupplierPriceUpdate,
): Promise<SupplierPriceOut> {
  const { data } = await api.patch<SupplierPriceOut>(
    `${suppliersUrl(firmId)}/${supplierId}/prices/${priceId}`,
    payload,
  );
  return data;
}

/** Takes one row out of a supplier's list. 204 with no body. */
export async function removePrice(
  firmId: number,
  supplierId: number,
  priceId: number,
): Promise<void> {
  await api.post(
    `${suppliersUrl(firmId)}/${supplierId}/prices/${priceId}/deactivate`,
  );
}
