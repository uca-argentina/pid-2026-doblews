import { api } from "../../lib/api";
import type { RecipeOut, ResourceOut } from "./types";

/** The catalogue reads. Under the firm because catalog.view is a firm-scope
 * permission; the rows are the same whichever firm asks (ADR-003 section 7). */

function catalogUrl(firmId: number): string {
  return `/firms/${firmId}/catalog`;
}

/** Every active recipe with its lines, ordered by name. */
export async function fetchRecipes(firmId: number): Promise<RecipeOut[]> {
  const { data } = await api.get<RecipeOut[]>(`${catalogUrl(firmId)}/recipes`);
  return data;
}

/** Every active material with its reference price, ordered by name. */
export async function fetchResources(firmId: number): Promise<ResourceOut[]> {
  const { data } = await api.get<ResourceOut[]>(
    `${catalogUrl(firmId)}/resources`,
  );
  return data;
}
