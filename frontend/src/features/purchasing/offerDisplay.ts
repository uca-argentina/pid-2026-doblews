import dayjs from "dayjs";
import { formatMoney } from "../../lib/format";
import type { OfferOut } from "./types";

/** How an offer's numbers read, shared by the table and the cards so the two
 * shapes cannot word them differently. */

/** "Sin cargo" for a zero, rather than a "$ 0,00" that reads like a gap —
 * the same wording as the supplier's own list. */
export function shippingText(offer: OfferOut, currency: string): string {
  return Number(offer.shipping_cost) === 0
    ? "Sin cargo"
    : formatMoney(offer.shipping_cost, currency);
}

export function updatedOnText(offer: OfferOut): string {
  return dayjs(offer.price_updated_at).format("DD/MM/YYYY");
}

/** The offers that tie for cheapest: one, or several when they tie. */
export function cheapestOffers(offers: OfferOut[]): OfferOut[] {
  return offers.filter((offer) => offer.cheapest);
}

/** "A", "A y B", "A, B y C". */
export function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}`;
}
