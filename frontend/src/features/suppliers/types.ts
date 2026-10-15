// Mirrors backend/app/schemas/supplier.py field for field, in the wire's own
// snake_case like every other types.ts here. Money arrives and leaves as
// decimal strings ("230.00"), never as numbers, and stays a string until
// lib/format.ts prints it.

import type { UnitRef } from "../catalog/types";

/** One supplier of the listing, with how long its price list is. */
export interface SupplierOut {
  id: number;
  name: string;
  contact_name: string | null;
  contact_email: string | null;
  phone: string | null;
  address: string | null;
  price_count: number;
}

/** The create and edit form of a supplier. Every field is sent on an edit, so
 * a field left empty is cleared (the API is a PATCH: null clears, absent keeps). */
export interface SupplierWrite {
  name: string;
  contact_name: string | null;
  contact_email: string | null;
  phone: string | null;
  address: string | null;
}

/** The material a row prices, with the price the budget computes with. Shown
 * beside the supplier's own so a screen can always say which one it displays
 * (ADR-010 section 5). */
export interface PricedResource {
  id: number;
  name: string;
  unit: UnitRef;
  reference_price: string;
}

/** One row of a supplier's price list. */
export interface SupplierPriceOut {
  id: number;
  resource: PricedResource;
  /** Per ONE unit of the material, in the unit the catalogue gives it. */
  unit_price: string;
  /** A fixed amount per material, whatever the quantity. "0.00" if free. */
  shipping_cost: string;
  currency: string;
  /** An instant (ISO 8601 with offset): moves only when an amount changes. */
  price_updated_at: string;
}

/** A supplier with its whole price list. */
export interface SupplierDetailOut extends SupplierOut {
  prices: SupplierPriceOut[];
}

export interface SupplierPriceCreate {
  resource_id: number;
  unit_price: string;
  shipping_cost: string;
}

/** The material of a row is not editable: to price another one, remove the
 * row and add the other. */
export interface SupplierPriceUpdate {
  unit_price: string;
  shipping_cost: string;
}
