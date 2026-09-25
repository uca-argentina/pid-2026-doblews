import { api } from "../../lib/api";
import type { RecipeOut, RecipeWrite, ResourceOut } from "./types";

/** The catalogue as a firm sees it. Under the firm because catalog.view is a
 * firm-scope permission. Resources and general recipes are the same whichever
 * firm asks (ADR-003 section 7); the firm's own recipes are only its own, and
 * writing them needs recipe.manage (HU-9, ADR-006). */

function catalogUrl(firmId: number): string {
  return `/firms/${firmId}/catalog`;
}

/** Every active recipe the firm can use — the general ones and its own, each
 * with its origin — with its lines, ordered by name. */
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

/** Adds a recipe of this firm. */
export async function createFirmRecipe(
  firmId: number,
  payload: RecipeWrite,
): Promise<RecipeOut> {
  const { data } = await api.post<RecipeOut>(
    `${catalogUrl(firmId)}/recipes`,
    payload,
  );
  return data;
}

/** Replaces one of this firm's recipes. A general one is a 404. */
export async function updateFirmRecipe(
  firmId: number,
  recipeId: number,
  payload: RecipeWrite,
): Promise<RecipeOut> {
  const { data } = await api.put<RecipeOut>(
    `${catalogUrl(firmId)}/recipes/${recipeId}`,
    payload,
  );
  return data;
}

/** Logical deactivation of one of this firm's recipes. 204 with no body. */
export async function deactivateFirmRecipe(
  firmId: number,
  recipeId: number,
): Promise<void> {
  await api.delete(`${catalogUrl(firmId)}/recipes/${recipeId}`);
}
