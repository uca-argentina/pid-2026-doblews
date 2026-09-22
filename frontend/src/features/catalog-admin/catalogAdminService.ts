import { api } from "../../lib/api";
import type {
  RecipeOut,
  RecipeWrite,
  ResourceOut,
  ResourceWrite,
} from "./types";

/** Every call the catalogue admin screens make (HU-8). One module so the
 * URLs live in one place, and the hooks in useCatalogAdmin.ts stay about
 * caching.
 *
 * Nothing here hangs off /firms/{id}: the catalogue belongs to no firm, and
 * these routes are guarded by catalog.manage in platform scope, like
 * platformService.ts's /platform/firms. */

const RESOURCES_URL = "/platform/catalog/resources";
const RECIPES_URL = "/platform/catalog/recipes";

/** Every active resource, the same rows HU-4's own catalogue shows. */
export async function fetchAdminResources(): Promise<ResourceOut[]> {
  const { data } = await api.get<ResourceOut[]>(RESOURCES_URL);
  return data;
}

export async function createResource(
  payload: ResourceWrite,
): Promise<ResourceOut> {
  const { data } = await api.post<ResourceOut>(RESOURCES_URL, payload);
  return data;
}

export async function updateResource(
  resourceId: number,
  payload: ResourceWrite,
): Promise<ResourceOut> {
  const { data } = await api.put<ResourceOut>(
    `${RESOURCES_URL}/${resourceId}`,
    payload,
  );
  return data;
}

/** Logical deactivation. 204 with no body. */
export async function deactivateResource(resourceId: number): Promise<void> {
  await api.delete(`${RESOURCES_URL}/${resourceId}`);
}

/** Every active recipe with its lines, the same rows HU-4's own catalogue
 * shows. */
export async function fetchAdminRecipes(): Promise<RecipeOut[]> {
  const { data } = await api.get<RecipeOut[]>(RECIPES_URL);
  return data;
}

export async function createRecipe(payload: RecipeWrite): Promise<RecipeOut> {
  const { data } = await api.post<RecipeOut>(RECIPES_URL, payload);
  return data;
}

export async function updateRecipe(
  recipeId: number,
  payload: RecipeWrite,
): Promise<RecipeOut> {
  const { data } = await api.put<RecipeOut>(
    `${RECIPES_URL}/${recipeId}`,
    payload,
  );
  return data;
}

/** Logical deactivation. No usage guard, unlike a resource's: the works that
 * already added this recipe keep computing from it. */
export async function deactivateRecipe(recipeId: number): Promise<void> {
  await api.delete(`${RECIPES_URL}/${recipeId}`);
}
