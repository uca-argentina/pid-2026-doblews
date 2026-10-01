// Mirrors backend/app/schemas/budget.py field for field, in the wire's own
// snake_case. Quantities and money arrive as decimal strings and stay strings
// until lib/format.ts prints them.

import type { UnitRef } from "../catalog/types";
import type { ResourceType } from "../catalog/resourceTypes";

/** One resource of the budget: how much of it, at what price, for how much. */
export interface BudgetItemOut {
  resource_id: number;
  name: string;
  unit: UnitRef;
  quantity: string;
  /** The reference price of one unit: per brick, and per hour for labour and
   * equipment, whose unit is `h` (T-06). */
  unit_price: string;
  subtotal: string;
}

/** One of the three groups. All three always arrive, empty ones included, so
 * the screen decides what to render instead of inferring it from what came. */
export interface BudgetGroupOut {
  type: ResourceType;
  items: BudgetItemOut[];
  subtotal: string;
}

/** GET .../projects/{projectId}/budget. No field is nullable here, unlike the
 * take-off: the whole endpoint is behind project.cost.view, so whoever gets an
 * answer gets the numbers. */
export interface BudgetOut {
  groups: BudgetGroupOut[];
  total: string;
  currency: string;
  /** An instant: the oldest price the budget is built from, for "precios de
   * referencia al <fecha>". null when the work has no lines to price. */
  prices_as_of: string | null;
}

/** What BudgetGroupSection renders, which both the draft and a saved version
 * can supply.
 *
 * The unit is the abbreviation alone and not a UnitRef, because that is all a
 * frozen item has: a version copies the abbreviation it was saved with instead
 * of referencing the unit catalogue (ADR-007 section 2). The draft adapts down
 * to this rather than the version inventing a code it never stored. */
export interface BudgetSectionItem {
  resource_id: number;
  name: string;
  unit_abbreviation: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
}

export interface BudgetSectionGroup {
  type: ResourceType;
  items: BudgetSectionItem[];
  subtotal: string;
}

/** The draft's groups in the shape above: its items carry a full UnitRef, of
 * which only the abbreviation reaches the screen. */
export function toSectionGroups(
  groups: BudgetGroupOut[],
): BudgetSectionGroup[] {
  return groups.map((group) => ({
    type: group.type,
    subtotal: group.subtotal,
    items: group.items.map((item) => ({
      resource_id: item.resource_id,
      name: item.name,
      unit_abbreviation: item.unit.abbreviation,
      quantity: item.quantity,
      unit_price: item.unit_price,
      subtotal: item.subtotal,
    })),
  }));
}
