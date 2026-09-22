import { useQuery } from "@tanstack/react-query";
import { fetchRecipes, fetchResources } from "./catalogService";

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
