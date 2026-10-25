import type { OfferOut, ProjectPurchasingItem } from "./types";

/** What HU-20 asks of a material of the work's comparison before ordering it. */

/** How much of the material the work still has to order: the take-off's
 * quantity minus what is already on order, drafts included. */
export function pendingQuantity(item: ProjectPurchasingItem): number {
  return Number(item.quantity) - Number(item.ordered_quantity);
}

/** Whether a material can go into an order: someone sells it, and the work
 * still needs some of it. */
export function canOrder(item: ProjectPurchasingItem): boolean {
  return item.offers.length > 0 && pendingQuantity(item) > 0;
}

/** What an offer costs for this quantity: round(price × quantity, 2) plus the
 * shipping, the backend's offer_total, so a supplier's option in the picker
 * reads the amount its draft will carry. */
export function offerTotalFor(offer: OfferOut, quantity: number): number {
  const goods = Math.round(Number(offer.unit_price) * quantity * 100) / 100;
  return goods + Number(offer.shipping_cost);
}
