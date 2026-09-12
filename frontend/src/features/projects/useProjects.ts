import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  archiveProject,
  createProject,
  fetchProject,
  fetchProjects,
  updateProject,
} from "./projectService";
import type { ProjectWrite } from "./types";

/** Query keys for everything about one firm's works.
 *
 * They hang under ["firm", firmId], the key FirmLayout already uses, so a
 * mutation can invalidate exactly this firm's works and nothing else. One work
 * hangs below the listing, so writing to it refreshes both with one call. */
export const projectKeys = {
  all: (firmId: number) => ["firm", firmId, "projects"] as const,
  one: (firmId: number, projectId: number) =>
    ["firm", firmId, "projects", projectId] as const,
};

/** The works of the active firm that the caller may see. */
export function useProjects(firmId: number) {
  return useQuery({
    queryKey: projectKeys.all(firmId),
    queryFn: () => fetchProjects(firmId),
  });
}

/** One work, with the caller's permissions on it.
 *
 * retry: false because the error to expect is a 404 meaning "not yours", and
 * asking again will not change that — the same reasoning as FirmLayout. */
export function useProject(firmId: number, projectId: number) {
  return useQuery({
    queryKey: projectKeys.one(firmId, projectId),
    queryFn: () => fetchProject(firmId, projectId),
    enabled: Number.isInteger(projectId) && projectId > 0,
    retry: false,
  });
}

/** Creates a work with the caller as its lead.
 *
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the listing has actually been refetched, so the modal closes onto a list
 * that already shows the new work instead of onto the old one.
 *
 * Errors are not handled here: the modal renders them itself, because a 409 —
 * the chosen client is no longer a client of this firm — is something the
 * architect can act on and belongs next to the form they were filling in. */
export function useCreateProject(firmId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: ProjectWrite) => createProject(firmId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: projectKeys.all(firmId) }),
  });
}

/** Saves the edit form over a work.
 *
 * Invalidating the listing key also invalidates that work's own key, since it
 * hangs below it: the detail screen and the list behind it both come back
 * fresh, permissions included. */
export function useUpdateProject(firmId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: { projectId: number; payload: ProjectWrite }) =>
      updateProject(firmId, variables.projectId, variables.payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: projectKeys.all(firmId) }),
  });
}

/** Archives a work. It leaves the listing and its own screen stops answering,
 * but the row and the team it had are untouched.
 *
 * exact: true, and this is the one mutation that needs it. Every other write
 * wants the whole subtree refreshed, because a work's own key hangs below the
 * listing's. Here that would refetch the work we just archived — from the
 * screen that is still mounted and showing it — and the backend would rightly
 * answer 404, which ProjectLayout reads as "this work is not yours" and turns
 * into a "no encontrada" notice on top of the success one.
 *
 * Narrowing it to the listing leaves the detail's cache entry untouched, so
 * nothing refetches it and the screen is gone a moment later anyway. */
export function useArchiveProject(firmId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: number) => archiveProject(firmId, projectId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: projectKeys.all(firmId),
        exact: true,
      }),
  });
}
