// Write shapes mirror backend/app/schemas/catalog_admin.py field for field,
// in the wire's own snake_case like every other types.ts here.
//
// The read shapes are the same rows HU-4 already types: the backend's admin
// GETs reuse services/catalog.py as is, so re-exporting instead of
// redefining is what keeps the two sides from drifting apart on their own.
export type {
  RecipeLineOut,
  RecipeLineWrite,
  RecipeOut,
  RecipeWrite,
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
