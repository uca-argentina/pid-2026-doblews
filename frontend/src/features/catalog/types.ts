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

/** A recipe with everything one unit of it takes. What HU-4's browser lists
 * and HU-5's "Agregar al cómputo" picks from. */
export interface RecipeOut {
  id: number;
  name: string;
  description: string | null;
  unit: UnitRef;
  lines: RecipeLineOut[];
}
