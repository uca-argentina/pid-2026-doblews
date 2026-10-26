// Mirrors backend/app/schemas/loyalty.py field for field, in the wire's own
// snake_case like every other types.ts here. Quantities arrive as decimal
// strings and stay strings until lib/format.ts prints them; points are whole
// numbers and arrive as numbers.

import type { UnitRef } from "../catalog/types";
import type { NamedRef } from "../purchase-orders/types";

/** The four fixed levels of ADR-012 section 5, lowest first. */
export type Level = "bronze" | "silver" | "gold" | "platinum";

export type PointsRule =
  | "same_material_similar_quantity"
  | "same_material"
  | "same_supplier"
  | "first_purchase";

/** Where a total stands, for the firm or with one supplier. The three next_*
 * fields are null together, at the top level. */
export interface LevelOut {
  points: number;
  level: Level;
  /** Where the current level starts, so the bar runs between two thresholds
   * instead of from zero. */
  level_from: number;
  next_level: Level | null;
  next_level_at: number | null;
  points_to_next: number | null;
}

export interface OrderRef {
  id: number;
  number: number;
}

/** One line of the history: what earned what, and why. */
export interface PointsEntryOut {
  id: number;
  earned_at: string;
  points: number;
  rule: PointsRule;
  quantity: string;
  /** What it was compared against, or null for the two rules that compare
   * nothing. */
  previous_quantity: string | null;
  order: OrderRef;
  project: NamedRef;
  supplier: NamedRef;
  resource: NamedRef;
  unit: UnitRef;
}

export interface LoyaltyOut {
  firm: LevelOut;
  /** Newest first. */
  history: PointsEntryOut[];
}
