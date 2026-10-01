// Mirrors backend/app/schemas/budget_version.py field for field, in the wire's
// own snake_case. Money and quantities arrive as decimal strings and stay
// strings until lib/format.ts prints them.

import type { ResourceType } from "../catalog/resourceTypes";

/** One row of the versions listing: enough to choose one, not to read it. */
export interface BudgetVersionSummary {
  id: number;
  version_number: number;
  note: string | null;
  total: string;
  currency: string;
  created_at: string;
  created_by_name: string;
}

/** One frozen resource. Its unit is the abbreviation as it was saved, not a
 * reference to the unit catalogue: a receipt has to render even if that row
 * changed since. */
export interface BudgetVersionItemOut {
  resource_id: number;
  name: string;
  unit_abbreviation: string;
  quantity: string;
  unit_price: string;
  subtotal: string;
}

export interface BudgetVersionGroupOut {
  type: ResourceType;
  items: BudgetVersionItemOut[];
  subtotal: string;
}

/** One take-off line as it stood when the version was saved. The recipe's name
 * is read live: a renamed recipe is still the same recipe. */
export interface BudgetVersionLineOut {
  recipe_id: number;
  recipe_name: string;
  quantity: string;
  note: string | null;
}

/** GET .../budget/versions/{id}: a saved version in full, read-only.
 *
 * total is the stored number, not a sum recomputed here — it is what was on
 * screen the day it was agreed. */
export interface BudgetVersionOut {
  id: number;
  version_number: number;
  note: string | null;
  groups: BudgetVersionGroupOut[];
  lines: BudgetVersionLineOut[];
  total: string;
  currency: string;
  /** When those prices were current, which is not today. */
  prices_as_of: string;
  created_at: string;
  created_by_name: string;
}

/** The save form. Nothing about the numbers travels: what gets frozen is what
 * the server computes at that moment. */
export interface BudgetVersionCreate {
  note: string | null;
}

/** What loading a version actually did. skipped carries the recipes that were
 * in the version and are no longer available, by name. */
export interface BudgetVersionLoadOut {
  loaded: number;
  skipped: string[];
}
