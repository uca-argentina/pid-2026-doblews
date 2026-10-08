import dayjs from "dayjs";
import { formatMoney } from "../../lib/format";
import type { SupplierPriceOut } from "./types";

/** How a row's numbers read, shared by the table and the cards so the two
 * screens cannot word them differently.
 *
 * Every amount says which price it is (ADR-010 section 5): the supplier's own,
 * and the reference one the budget computes with. */

export function supplierPriceText(price: SupplierPriceOut): string {
  return `${formatMoney(price.unit_price, price.currency)} por ${price.resource.unit.abbreviation}`;
}

export function referencePriceText(price: SupplierPriceOut): string {
  return `${formatMoney(price.resource.reference_price, price.currency)} por ${price.resource.unit.abbreviation}`;
}

/** "Sin cargo" for a zero, rather than a "$ 0,00" that reads like a gap. */
export function shippingText(price: SupplierPriceOut): string {
  return Number(price.shipping_cost) === 0
    ? "Sin cargo"
    : formatMoney(price.shipping_cost, price.currency);
}

export function updatedOnText(price: SupplierPriceOut): string {
  return dayjs(price.price_updated_at).format("DD/MM/YYYY");
}
