// Mirrors backend/app/schemas/purchase_order.py field for field, in the wire's
// own snake_case like every other types.ts here. Money and quantities arrive as
// decimal strings and stay strings until lib/format.ts prints them.

import type { UnitRef } from "../catalog/types";

export interface NamedRef {
  id: number;
  name: string;
}

/** The five states of ADR-011 section 3. HU-21 issues and cancels; the
 * received ones come with HU-22. */
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

/** One line of an order, at the price it froze when it was made. */
export interface PurchaseOrderLineOut {
  id: number;
  resource: NamedRef;
  unit: UnitRef;
  quantity: string;
  unit_price: string;
  shipping_cost: string;
  estimated_total: string;
}

/** One change of status: what, when and who (HU-21). */
export interface OrderEvent {
  kind: "created" | "issued" | "cancelled";
  at: string;
  by: NamedRef;
}

export interface PurchaseOrderOut extends PurchaseOrderSummary {
  lines: PurchaseOrderLineOut[];
  /** Oldest first. */
  history: OrderEvent[];
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
