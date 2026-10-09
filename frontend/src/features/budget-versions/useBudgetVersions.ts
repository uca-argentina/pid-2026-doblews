import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import {
  fetchVersion,
  fetchVersions,
  loadVersion,
  saveVersion,
} from "./budgetVersionsService";
import type { BudgetVersionCreate } from "./types";

/** Versions hang below their work's key, like the budget and the take-off. */
export const versionKeys = {
  all: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "budget-versions"] as const,
  one: (firmId: number, projectId: number, versionId: number) =>
    [...versionKeys.all(firmId, projectId), versionId] as const,
};

/** Every saved version of one work, newest first.
 *
 * `enabled` is for the take-off, which reads the listing to say which version
 * it matches and must not ask on behalf of whoever may not see costs: the
 * endpoint answers 403 to the project client. */
export function useBudgetVersions(
  firmId: number,
  projectId: number,
  enabled = true,
) {
  return useQuery({
    queryKey: versionKeys.all(firmId, projectId),
    queryFn: () => fetchVersions(firmId, projectId),
    enabled,
  });
}

/** One saved version in full.
 *
 * staleTime: Infinity, which is the one place in this app where that is a
 * statement about the data and not a cache tuning: a version cannot change.
 * There is no endpoint that could change it (ADR-007 section 5, rule 2), so
 * refetching one would always return the same bytes. */
export function useBudgetVersion(
  firmId: number,
  projectId: number,
  versionId: number,
) {
  return useQuery({
    queryKey: versionKeys.one(firmId, projectId, versionId),
    queryFn: () => fetchVersion(firmId, projectId, versionId),
    staleTime: Infinity,
    enabled: Number.isInteger(versionId) && versionId > 0,
  });
}

/** Saves a version. Invalidates the listing, and nothing else: the draft it
 * froze is untouched by freezing it. */
export function useSaveVersion(firmId: number, projectId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: BudgetVersionCreate) =>
      saveVersion(firmId, projectId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: versionKeys.all(firmId, projectId),
      }),
  });
}

/** Loads a version into the draft.
 *
 * Invalidates the whole projects subtree of this firm and not just the budget,
 * because this write replaces the take-off: the cómputo screen, the budget and
 * every total hanging off them are all stale at once. The versions themselves
 * hang below the same key and are refetched too, which costs one request and
 * saves reasoning about which of the three caches this touched. */
export function useLoadVersion(firmId: number, projectId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (versionId: number) =>
      loadVersion(firmId, projectId, versionId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: projectKeys.all(firmId) }),
  });
}
