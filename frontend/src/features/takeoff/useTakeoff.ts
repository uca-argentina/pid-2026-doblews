import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import {
  createLine,
  fetchTakeoff,
  removeLine,
  setLineTask,
  updateLine,
} from "./takeoffService";
import type { TakeoffLineCreate, TakeoffLineUpdate } from "./types";

/** The take-off hangs below its work's key, so editing the work (which
 * invalidates the whole projects subtree) refreshes it too, and nothing about
 * another work or firm is touched by a write here. */
export const takeoffKeys = {
  one: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "takeoff"] as const,
};

/** The take-off of one work: lines, materials and totals together. */
export function useTakeoff(firmId: number, projectId: number) {
  return useQuery({
    queryKey: takeoffKeys.one(firmId, projectId),
    queryFn: () => fetchTakeoff(firmId, projectId),
  });
}

/** Every write below refreshes the same single query, because a line changes
 * the totals as well as the list. Returning the invalidation from onSuccess
 * keeps the mutation pending until the refetch lands, so a modal closes onto a
 * take-off that already shows the change.
 *
 * Errors are not handled here: the modals render them next to the form, where
 * a 409 about a retired recipe can be acted on. */
function useTakeoffWrite<Variables, Result>(
  firmId: number,
  projectId: number,
  write: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: write,
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: takeoffKeys.one(firmId, projectId),
      }),
  });
}

/** Loads a recipe onto the work. */
export function useCreateLine(firmId: number, projectId: number) {
  return useTakeoffWrite(firmId, projectId, (payload: TakeoffLineCreate) =>
    createLine(firmId, projectId, payload),
  );
}

/** Saves the edit form of one line. */
export function useUpdateLine(firmId: number, projectId: number) {
  return useTakeoffWrite(
    firmId,
    projectId,
    (variables: { lineId: number; payload: TakeoffLineUpdate }) =>
      updateLine(firmId, projectId, variables.lineId, variables.payload),
  );
}

/** Removes one line from the take-off. */
export function useRemoveLine(firmId: number, projectId: number) {
  return useTakeoffWrite(firmId, projectId, (lineId: number) =>
    removeLine(firmId, projectId, lineId),
  );
}

/** Assigns one line to a task, or to none (HU-13).
 *
 * Refreshes the take-off only. The planning shows the same link from the
 * other side, but it is another tab: its query is refetched when that screen
 * mounts, so there is nothing on screen here to keep in step with it. */
export function useSetLineTask(firmId: number, projectId: number) {
  return useTakeoffWrite(
    firmId,
    projectId,
    (variables: { lineId: number; taskId: number | null }) =>
      setLineTask(firmId, projectId, variables.lineId, variables.taskId),
  );
}
