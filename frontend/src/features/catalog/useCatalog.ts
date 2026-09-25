import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { RecipeWriter } from "../recipes/types";
import {
  createFirmRecipe,
  deactivateFirmRecipe,
  fetchRecipes,
  fetchResources,
  updateFirmRecipe,
} from "./catalogService";
import type { RecipeWrite } from "./types";

/** Query keys for the catalogue, under ["firm", firmId] like everything else a
 * firm screen reads, because that is the firm the permission was checked
 * against. The data is the same for every firm; the cache entry per firm is the
 * price of keeping the keys uniform, and it is a few kilobytes. */
export const catalogKeys = {
  recipes: (firmId: number) => ["firm", firmId, "catalog", "recipes"] as const,
  resources: (firmId: number) =>
    ["firm", firmId, "catalog", "resources"] as const,
};

/** Ten minutes: the catalogue changes by migration today, and by hand at most
 * once HU-8 exists. Long enough that opening the catalogue page and then HU-5's
 * picker reuses one request; not Infinity, because a price edited in HU-8 must
 * reach a screen left open without a reload. */
const CATALOG_STALE_TIME = 10 * 60 * 1000;

/** The recipes of the catalogue, each with its lines. Shared by the catalogue
 * page and, in HU-5, by the "Agregar al cómputo" picker. */
export function useRecipes(firmId: number) {
  return useQuery({
    queryKey: catalogKeys.recipes(firmId),
    queryFn: () => fetchRecipes(firmId),
    staleTime: CATALOG_STALE_TIME,
  });
}

/** The materials of the catalogue, with their reference prices. */
export function useResources(firmId: number) {
  return useQuery({
    queryKey: catalogKeys.resources(firmId),
    queryFn: () => fetchResources(firmId),
    staleTime: CATALOG_STALE_TIME,
  });
}

/** HU-9's side of the shared recipe modals: this firm's endpoints.
 *
 * Every write refreshes catalogKeys.recipes(firmId), the one cache the
 * catalogue page and HU-5's picker both read, so a recipe created here is
 * offered in "Agregar al cómputo" without a reload. Returning the invalidation
 * keeps the mutation pending until the list has refetched, so the modal
 * closes onto a list that already shows the change — same as HU-8's hooks. */
export function useFirmRecipeWriter(firmId: number): RecipeWriter {
  const queryClient = useQueryClient();
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: catalogKeys.recipes(firmId) });

  const create = useMutation({
    mutationFn: (payload: RecipeWrite) => createFirmRecipe(firmId, payload),
    onSuccess: refresh,
  });
  const update = useMutation({
    mutationFn: (variables: { recipeId: number; payload: RecipeWrite }) =>
      updateFirmRecipe(firmId, variables.recipeId, variables.payload),
    onSuccess: refresh,
  });
  const deactivate = useMutation({
    mutationFn: (recipeId: number) => deactivateFirmRecipe(firmId, recipeId),
    onSuccess: refresh,
  });

  return {
    save: (payload, recipeId) =>
      recipeId === null
        ? create.mutateAsync(payload)
        : update.mutateAsync({ recipeId, payload }),
    saving: create.isPending || update.isPending,
    deactivate: (recipeId) => deactivate.mutateAsync(recipeId),
    deactivating: deactivate.isPending,
  };
}
