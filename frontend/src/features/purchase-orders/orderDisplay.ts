import dayjs from "dayjs";
import type {
  OrderEvent,
  OrderStatus,
  PurchaseOrderOut,
  PurchaseOrderSummary,
} from "./types";

/** How an order reads on every screen, in one place so the listing, the
 * detail and the notifications cannot word it differently. */

/** 7 → "OC-0007": the number is correlative per firm (ADR-011 section 4). */
export function orderNumber(number: number): string {
  return `OC-${String(number).padStart(4, "0")}`;
}

export const STATUS_LABELS: Record<OrderStatus, string> = {
  draft: "Borrador",
  issued: "Emitida",
  partially_received: "Recibida parcialmente",
  received: "Recibida",
  cancelled: "Anulada",
};

export const STATUS_COLORS: Record<OrderStatus, string> = {
  draft: "gray",
  issued: "blue",
  partially_received: "yellow",
  received: "obra",
  cancelled: "red",
};

/** Each event of an order's history, as the detail lists it (HU-21). */
export const EVENT_LABELS: Record<OrderEvent["kind"], string> = {
  created: "Creada",
  issued: "Emitida",
  cancelled: "Anulada",
};

/** "25/10/2026 14:30", in the viewer's own time zone. */
export function formatDateTime(value: string): string {
  return dayjs(value).format("DD/MM/YYYY HH:mm");
}

/** Which way an order can still go, so a screen offers only those (ADR-011
 * section 3). The backend answers 409 to anything else. */
export function canIssue(order: PurchaseOrderOut): boolean {
  return order.status === "draft" && order.lines.length > 0;
}

export function canCancel(order: PurchaseOrderSummary): boolean {
  return order.status === "draft" || order.status === "issued";
}
