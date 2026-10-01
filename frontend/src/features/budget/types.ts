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
