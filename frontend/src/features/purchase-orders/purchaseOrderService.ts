import { api } from "../../lib/api";
import type {
  GenerateOrdersOut,
  OrderStatus,
  PurchaseOrderOut,
  PurchaseOrderSummary,
} from "./types";

/** Every call the purchase order screens make (ADR-011 section 8).
 *
 * Two prefixes, as in the backend: generating and listing live under the
 * work; reading and editing one order live under the firm, which is what lets
 * an architect who is not on the work's team manage it. */

function firmOrdersUrl(firmId: number): string {
  return `/firms/${firmId}/purchase-orders`;
}

function projectOrdersUrl(firmId: number, projectId: number): string {
  return `/firms/${firmId}/projects/${projectId}/purchase-orders`;
}

/** Drafts for these materials of the work, one per supplier. */
export async function generateOrders(
  firmId: number,
  projectId: number,
  resourceIds: number[],
): Promise<GenerateOrdersOut> {
  const { data } = await api.post<GenerateOrdersOut>(
    `${projectOrdersUrl(firmId, projectId)}/generate`,
    { resource_ids: resourceIds },
  );
  return data;
}

/** The work's orders, newest first, optionally of one status. */
export async function fetchProjectOrders(
  firmId: number,
  projectId: number,
  status?: OrderStatus,
): Promise<PurchaseOrderSummary[]> {
  const { data } = await api.get<PurchaseOrderSummary[]>(
    projectOrdersUrl(firmId, projectId),
    { params: status ? { order_status: status } : undefined },
  );
  return data;
}

/** One order with its lines. A 404 covers another firm's and a discarded draft. */
export async function fetchOrder(
  firmId: number,
  orderId: number,
): Promise<PurchaseOrderOut> {
  const { data } = await api.get<PurchaseOrderOut>(
    `${firmOrdersUrl(firmId)}/${orderId}`,
  );
  return data;
}

export async function addLine(
  firmId: number,
  orderId: number,
  payload: { resource_id: number; quantity: string },
): Promise<PurchaseOrderOut> {
  const { data } = await api.post<PurchaseOrderOut>(
    `${firmOrdersUrl(firmId)}/${orderId}/lines`,
    payload,
  );
  return data;
}

export async function updateLine(
  firmId: number,
  orderId: number,
  lineId: number,
  quantity: string,
): Promise<PurchaseOrderOut> {
  const { data } = await api.patch<PurchaseOrderOut>(
    `${firmOrdersUrl(firmId)}/${orderId}/lines/${lineId}`,
    { quantity },
  );
  return data;
}

/** Moves the line to the work's draft for that supplier. Answers with the
 * draft it landed in, which is usually another order. */
export async function changeLineSupplier(
  firmId: number,
  orderId: number,
  lineId: number,
  supplierId: number,
): Promise<PurchaseOrderOut> {
  const { data } = await api.post<PurchaseOrderOut>(
    `${firmOrdersUrl(firmId)}/${orderId}/lines/${lineId}/supplier`,
    { supplier_id: supplierId },
  );
  return data;
}

/** Takes a line out of a draft. A POST and not a DELETE: nothing is erased. */
export async function deactivateLine(
  firmId: number,
  orderId: number,
  lineId: number,
): Promise<PurchaseOrderOut> {
  const { data } = await api.post<PurchaseOrderOut>(
    `${firmOrdersUrl(firmId)}/${orderId}/lines/${lineId}/deactivate`,
  );
  return data;
}

/** Discards a draft. 204 with no body. */
export async function discardOrder(
  firmId: number,
  orderId: number,
): Promise<void> {
  await api.post(`${firmOrdersUrl(firmId)}/${orderId}/discard`);
}
