import type { OrderStatus } from "./types";

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
