// Mirrors backend/app/schemas/purchasing.py field for field, in the wire's own
// snake_case like every other types.ts here. Money and quantities arrive as
// decimal strings and stay strings until lib/format.ts prints them.

import type { UnitRef } from "../catalog/types";

/** One supplier's offer for a material, at the quantity being compared. */
export interface OfferOut {
  supplier_id: number;
  supplier_name: string;
  /** Per ONE unit of the material. */
  unit_price: string;
  /** A fixed amount per material, whatever the quantity. "0.00" if free. */
  shipping_cost: string;
  /** round(unit_price × quantity, 2) + shipping_cost. */
  total: string;
  /** True for every offer tied at the lowest total, not only the first. */
  cheapest: boolean;
  price_updated_at: string;
}

/** A material, the quantity it is compared at, and every offer for it,
 * cheapest first. No offers means no live supplier lists it: "sin proveedor". */
export interface ComparedMaterial {
  resource_id: number;
  name: string;
  unit: UnitRef;
  quantity: string;
  /** The catalogue's price, the one the budget computes with (ADR-010 section 5). */
  reference_price: string;
  /** The same quantity at the reference price. */
  reference_total: string;
  offers: OfferOut[];
}

/** The comparison for one material, from the suppliers section. */
export interface MaterialComparisonOut extends ComparedMaterial {
  currency: string;
  has_suppliers: boolean;
}

/** Each material of a work's take-off, compared at the quantity the work
 * needs. No grand total: HU-18 leaves an optimal purchase out. */
export interface ProjectPurchasingOut {
  items: ComparedMaterial[];
  currency: string;
  has_suppliers: boolean;
}
