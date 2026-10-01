import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createRecipe,
  createResource,
  deactivateRecipe,
  deactivateResource,
  fetchAdminRecipes,
  fetchAdminResources,
  updateRecipe,
  updateResource,
} from "./catalogAdminService";
import type { RecipeWriter } from "../recipes/types";
import type { RecipeWrite, ResourceWrite } from "./types";

/** Query keys for the catalogue admin screens.
 *
 * Under ["platform", "catalog", ...] and not ["firm", id, "catalog", ...]:
 * this is the platform's own write surface over the catalogue, a different
 * cache from the firm-scoped read-only one HU-4's useCatalog.ts keeps, and
 * invalidating one must never touch the other. */
export const catalogAdminKeys = {
  resources: () => ["platform", "catalog", "resources"] as const,
  recipes: () => ["platform", "catalog", "recipes"] as const,
};

/** Every active resource. No staleTime override: unlike the units of
 * measure, this catalogue is meant to change by hand from this very
 * screen. */
export function useAdminResources() {
  return useQuery({
    queryKey: catalogAdminKeys.resources(),
    queryFn: fetchAdminResources,
  });
}

/** Every active recipe with its lines. */
export function useAdminRecipes() {
  return useQuery({
    queryKey: catalogAdminKeys.recipes(),
    queryFn: fetchAdminRecipes,
  });
}

/** Creates a resource.
 *
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the listing has been refetched, so the modal closes onto a list that
 * already shows the new row — same pattern as useCreateFirm.
 *
 * Errors are not handled here: the form renders them next to the fields,
 * since a 409 ("ya existe un material activo con ese nombre") is something
 * support can act on. */
export function useCreateResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ResourceWrite) => createResource(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.resources() }),
  });
}

export function useUpdateResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: { resourceId: number; payload: ResourceWrite }) =>
      updateResource(variables.resourceId, variables.payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.resources() }),
  });
}

/** Deactivates a resource. Refused with 409 while an active recipe still
 * uses it — the form/modal calling this surfaces that text as is. */
export function useDeactivateResource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (resourceId: number) => deactivateResource(resourceId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.resources() }),
  });
}

export function useCreateRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: RecipeWrite) => createRecipe(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.recipes() }),
  });
}

export function useUpdateRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: { recipeId: number; payload: RecipeWrite }) =>
      updateRecipe(variables.recipeId, variables.payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.recipes() }),
  });
}

/** Deactivates a recipe. No usage guard on the backend, unlike a resource's:
 * the works that already added it keep computing from it. */
export function useDeactivateRecipe() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (recipeId: number) => deactivateRecipe(recipeId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogAdminKeys.recipes() }),
  });
}

/** HU-8's side of the shared recipe modals: support's endpoints, and the
 * platform cache they refresh. */
export function useAdminRecipeWriter(): RecipeWriter {
  const createRecipe = useCreateRecipe();
  const updateRecipe = useUpdateRecipe();
  const deactivateRecipe = useDeactivateRecipe();

  return {
    save: (payload, recipeId) =>
      recipeId === null
        ? createRecipe.mutateAsync(payload)
        : updateRecipe.mutateAsync({ recipeId, payload }),
    saving: createRecipe.isPending || updateRecipe.isPending,
    deactivate: (recipeId) => deactivateRecipe.mutateAsync(recipeId),
    deactivating: deactivateRecipe.isPending,
  };
}
