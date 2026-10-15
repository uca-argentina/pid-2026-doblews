// Mirrors backend/app/schemas/takeoff.py field for field, in the wire's own
// snake_case like every other types.ts here. Quantities and money arrive as
// decimal strings ("7200.000", "1656000.00") and stay strings until
// lib/format.ts prints them.

import type { UnitRef } from "../catalog/types";
import type { ResourceType } from "../catalog/resourceTypes";

/** The recipe a line measures: enough to render it, not the catalogue card. */
export interface RecipeRef {
  id: number;
  name: string;
  unit: UnitRef;
}

/** The task of the planning a line is assigned to: enough to name it. */
export interface TaskRef {
  id: number;
  name: string;
}

/** One line of the take-off: this much of a recipe, maybe with a note that
 * tells it apart from another line of the same recipe ("planta baja"). */
export interface TakeoffLineOut {
  id: number;
  recipe: RecipeRef;
  /** In the recipe's own unit: "120.000" of a per-m2 wall is 120 m2. */
  quantity: string;
  note: string | null;
  /** The task this line is carried out in (HU-13), or null while it is
   * assigned to none. Its cost is what that task costs. */
  task: TaskRef | null;
}

/** One resource the work needs, summed across every line that uses it.
 *
 * Not only materials since T-06: a recipe also yields hours of labour and of
 * equipment (HU-10). `type` is what lets the screen show the three apart. */
export interface TakeoffMaterialOut {
  resource_id: number;
  name: string;
  type: ResourceType;
  unit: UnitRef;
  quantity: string;
  /** null when the caller may not see costs: the project client (ADR-003
   * section 8). The field is always there; only the value is withheld. */
  cost: string | null;
  currency: string;
}

/** GET .../projects/{projectId}/takeoff: the lines and what they add up to, in
 * one answer so the two never disagree on screen. */
export interface TakeoffOut {
  lines: TakeoffLineOut[];
  materials: TakeoffMaterialOut[];
  /** The sum of the materials' costs. "0.00" for an empty take-off, null when
   * the caller may not see costs. Not shown: the screen takes its total, and
   * every other price, from the budget. */
  total_cost: string | null;
  currency: string;
  /** An instant: the oldest price the costs are built from, for "precios de
   * referencia al <fecha>". null when there is nothing to price. */
  prices_as_of: string | null;
}

/** The add form. The quantity is a decimal string, never a number, so the
 * value typed is the value stored. */
export interface TakeoffLineCreate {
  recipe_id: number;
  quantity: string;
  note: string | null;
}

/** The edit form: a PUT of quantity and note. The recipe is not editable —
 * changing it would change the unit the quantity is expressed in. */
export interface TakeoffLineUpdate {
  quantity: string;
  note: string | null;
}
