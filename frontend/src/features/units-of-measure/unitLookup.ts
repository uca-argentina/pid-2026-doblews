import type { UnitOfMeasureOut } from "../units-of-measure/types";

/** Resolves a unit's code (what ResourceOut/RecipeOut.unit carries) back to
 * its id (what ResourceWrite/RecipeWrite need to send).
 *
 * The read shapes only carry {code, abbreviation} — a label, not the full
 * row — so editing an existing resource or recipe has to look its unit back
 * up in the closed catalogue to preload the write form's <Select>. Returns
 * null while the catalogue is still loading or the code is somehow unknown,
 * which leaves the field unset rather than throwing. */
export function findUnitId(
  units: UnitOfMeasureOut[] | undefined,
  code: string,
): number | null {
  return units?.find((unit) => unit.code === code)?.id ?? null;
}
