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

/** Each event of an order's history, as the detail lists it. */
export const EVENT_LABELS: Record<OrderEvent["kind"], string> = {
  created: "Creada",
  issued: "Emitida",
  cancelled: "Anulada",
  received: "Recepción registrada",
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

/** Whether a delivery may still be registered against the order (HU-22): one
 * that was issued and is not complete. A received order is closed. */
export function canReceive(order: PurchaseOrderSummary): boolean {
  return order.status === "issued" || order.status === "partially_received";
}

/** Whether the order is far enough along for what arrived to be worth columns
 * of its own. A draft and a cancelled order have nothing delivered. */
export function tracksDeliveries(order: PurchaseOrderSummary): boolean {
  return (
    order.status === "issued" ||
    order.status === "partially_received" ||
    order.status === "received"
  );
}

/** A line's difference as the table shows it: more than agreed reads as a
 * surcharge and less as a saving, so the sign is spelled out rather than left
 * to a minus sign the eye skips. Null while nothing arrived. */
export function differenceTone(difference: string | null): {
  color: string | undefined;
  prefix: string;
} {
  const value = Number(difference ?? 0);
  if (!difference || value === 0) return { color: undefined, prefix: "" };
  return value > 0
    ? { color: "red", prefix: "+" }
    : { color: "obra", prefix: "−" };
}

/** "26/10/2026" for a plain day, which is what a remito is dated by. */
export function formatDay(value: string): string {
  return dayjs(value).format("DD/MM/YYYY");
}
