// Mirrors backend/app/schemas/catalog.py field for field, in the wire's own
// snake_case like every other types.ts here.

/** The unit something is measured in: code to compare, abbreviation to show. */
export interface UnitRef {
  code: string;
  abbreviation: string;
}

/** One material of the catalogue, with its reference price.
 *
 * Money and quantities arrive as decimal strings ("230.00", "0.2500"), never
 * as numbers: the backend stores NUMERIC and a JSON number would bring float
 * rounding back in. They stay strings until lib/format.ts prints them. */
export interface ResourceOut {
  id: number;
  type: string;
  name: string;
  unit: UnitRef;
  reference_price: string;
  currency: string;
  /** An instant (ISO 8601 with offset): when this price was last set. */
  price_updated_at: string;
}

/** One line of a recipe: this much of a material per one unit of the recipe. */
export interface RecipeLineOut {
  resource_id: number;
  name: string;
  unit: UnitRef;
  quantity_per_unit: string;
  reference_price: string;
  currency: string;
}

/** Where a recipe comes from: the system catalogue support maintains, or the
 * firm's own (HU-9). What the cards badge, the browser filters by, and what
 * decides whether a card offers edit and deactivate at all. */
export type RecipeOrigin = "general" | "firm";

/** A recipe with everything one unit of it takes. What HU-4's browser lists
 * and HU-5's "Agregar al cómputo" picks from. */
export interface RecipeOut {
  id: number;
  name: string;
  description: string | null;
  unit: UnitRef;
  origin: RecipeOrigin;
  lines: RecipeLineOut[];
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
 * resource_id across lines (422) — the form validates both before sending.
 *
 * Here and not in catalog-admin because two screens send it: support's for a
 * general recipe (HU-8) and a firm's for its own (HU-9), to the same shape
 * (backend/app/schemas/catalog_admin.py's RecipeWrite). */
export interface RecipeWrite {
  name: string;
  description: string | null;
  unit_of_measure_id: number;
  lines: RecipeLineWrite[];
}
