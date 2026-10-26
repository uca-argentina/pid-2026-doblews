// Mirrors backend/app/schemas/purchase_order.py field for field, in the wire's
// own snake_case like every other types.ts here. Money and quantities arrive as
// decimal strings and stay strings until lib/format.ts prints them.

import type { UnitRef } from "../catalog/types";

export interface NamedRef {
  id: number;
  name: string;
}

/** The five states of ADR-011 section 3. The two received ones are never
 * chosen: the backend derives them from the order's receipts. */
export type OrderStatus =
  "draft" | "issued" | "partially_received" | "received" | "cancelled";

/** One order of a listing. */
export interface PurchaseOrderSummary {
  id: number;
  /** Correlative per firm; shown as OC-0001 (ADR-011 section 4). */
  number: number;
  status: OrderStatus;
  project: NamedRef;
  supplier: NamedRef;
  line_count: number;
  /** Sum of the lines' frozen price × quantity + shipping. */
  estimated_total: string;
  currency: string;
  created_at: string;
}

/** One line of an order, at the price it froze, and what has arrived of it. */
export interface PurchaseOrderLineOut {
  id: number;
  resource: NamedRef;
  unit: UnitRef;
  quantity: string;
  unit_price: string;
  shipping_cost: string;
  estimated_total: string;
  /** What arrived across the order's live receipts, and what is still owed. */
  received_quantity: string;
  pending_quantity: string;
  /** The two halves of the comparison, materials only on both sides: what the
   * frozen price says the delivered quantity should have cost, and what the
   * invoices charged for it. The freight is the receipt's (ADR-011 section 8). */
  received_estimate: string;
  actual_cost: string;
  /** actual_cost - received_estimate; positive is more than agreed. null while
   * nothing has arrived, when there is nothing to compare. */
  cost_difference: string | null;
}

/** One change of status: what, when and who (HU-21). A delivery is placed by
 * when it was loaded, not by the day it arrived. */
export interface OrderEvent {
  kind: "created" | "issued" | "cancelled" | "received";
  at: string;
  by: NamedRef;
}

/** What arrived of one line in one delivery, and what the invoice charged. */
export interface ReceiptLineOut {
  purchase_order_line_id: number;
  resource: NamedRef;
  unit: UnitRef;
  quantity: string;
  actual_cost: string;
}

/** One delivery of an order (HU-22). */
export interface ReceiptOut {
  id: number;
  received_on: string;
  note: string | null;
  /** The freight of this delivery, charged once for the whole truck. null is
   * "the supplier charged none". */
  shipping_cost: string | null;
  created_by: NamedRef;
  created_at: string;
  lines: ReceiptLineOut[];
  /** Materials plus freight. */
  total: string;
  /** Whether this is the one the order would let go of: the last loaded, on an
   * order that is not complete. Decided by the backend so the rule lives once. */
  can_cancel: boolean;
}

export interface PurchaseOrderOut extends PurchaseOrderSummary {
  lines: PurchaseOrderLineOut[];
  /** Oldest delivery first. */
  receipts: ReceiptOut[];
  /** Oldest first. */
  history: OrderEvent[];
  /** Every live receipt's materials and freight. */
  actual_total: string;
}

/** One material of a delivery as the form sends it. actual_cost carries no
 * freight: the delivery's freight is its own field. */
export interface ReceiptLineIn {
  line_id: number;
  quantity: string;
  actual_cost: string;
}

export interface ReceiptIn {
  received_on: string;
  note?: string | null;
  shipping_cost?: string | null;
  lines: ReceiptLineIn[];
}

/** A material to order and from whom; null is the cheapest. */
export interface GenerateItem {
  resource_id: number;
  supplier_id: number | null;
}

/** A material asked for that no draft got. */
export interface SkippedMaterial {
  resource_id: number;
  name: string;
  reason: "already_ordered" | "no_supplier";
}

export interface GenerateOrdersOut {
  orders: PurchaseOrderSummary[];
  skipped: SkippedMaterial[];
}
