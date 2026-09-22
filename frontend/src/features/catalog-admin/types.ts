// Write shapes mirror backend/app/schemas/catalog_admin.py field for field,
// in the wire's own snake_case like every other types.ts here.
//
// The read shapes are the same rows HU-4 already types: the backend's admin
// GETs reuse services/catalog.py as is, so re-exporting instead of
// redefining is what keeps the two sides from drifting apart on their own.
export type {
  RecipeLineOut,
  RecipeOut,
  ResourceOut,
  UnitRef,
} from "../catalog/types";

/** The closed set resource.type accepts (app/models/catalog.py's
 * RESOURCE_TYPE_CHECK). Sprint 1 only seeds "material"; the other two exist
 * for the day the team loads labour or equipment. */
export type ResourceType = "material" | "labor" | "equipment";

/** The create/edit form for one resource: a full replace, like ProjectWrite —
 * editing sends every field again, not a patch. */
export interface ResourceWrite {
  name: string;
  type: ResourceType;
  unit_of_measure_id: number;
  /** Decimal string ("9000.00"), scale 2 — never a number, same reason as
   * ResourceOut.reference_price. */
  reference_price: string;
}

/** One line of the master-detail form: this material, this much per unit. */
export interface RecipeLineWrite {
  resource_id: number;
  /** Decimal string, scale 4 (recipe_resource.quantity_per_unit is
   * NUMERIC(12,4) — a different scale from the take-off's NUMERIC(14,3)). */
  quantity_per_unit: string;
}

/** The create/edit form for one recipe: header and every one of its lines,
 * replaced whole. The backend rejects an empty lines array and a repeated
 * resource_id across lines (422) — the form validates both before sending. */
export interface RecipeWrite {
  name: string;
  description: string | null;
  unit_of_measure_id: number;
  lines: RecipeLineWrite[];
}
