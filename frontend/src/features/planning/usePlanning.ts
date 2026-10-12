import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import { takeoffKeys } from "../takeoff/useTakeoff";
import {
  createTask,
  fetchPlanning,
  fetchTaskAssignees,
  removeTask,
  setTaskLines,
  setTaskProgress,
  transitionTask,
  updateTask,
  updateTaskActualDates,
} from "./planningService";
import type { TaskActualDates, TaskTransition, TaskWrite } from "./types";

/** The planning hangs below its work's key, like the take-off, so editing the
 * work or its team (both invalidate the projects subtree) refreshes it too:
 * taking someone off the team is what leaves their tasks without assignee. */
export const planningKeys = {
  one: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "planning"] as const,
  assignees: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "planning-assignees"] as const,
};

/** The planning of one work: tasks, costs and totals together. */
export function usePlanning(firmId: number, projectId: number) {
  return useQuery({
    queryKey: planningKeys.one(firmId, projectId),
    queryFn: () => fetchPlanning(firmId, projectId),
  });
}

/** The options of the "responsable" <Select>. Only fetched by the form, which
 * only those who may manage the planning can open. */
export function useTaskAssignees(firmId: number, projectId: number) {
  return useQuery({
    queryKey: planningKeys.assignees(firmId, projectId),
    queryFn: () => fetchTaskAssignees(firmId, projectId),
  });
}

/** Every write below refreshes the planning and the take-off, and not only
 * the first.
 *
 * The two screens show the same link from each side: a task's cost is its
 * take-off lines, and each line of the take-off says which task it is in. So
 * assigning lines moves both, and so does removing a task, whose lines go back
 * to unassigned. Refreshing one alone would leave the other showing a link
 * that is no longer there. The remaining writes change the planning only, and
 * invalidating a query nobody is looking at costs nothing: it is refetched the
 * next time its screen mounts, which it would be anyway.
 *
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the refetch lands, so a modal closes onto a list that already shows the
 * change.
 *
 * Errors are not handled here: the modals render them next to the form, where
 * a 409 about a taken name or a status that moved can be acted on. */
function usePlanningWrite<Variables, Result>(
  firmId: number,
  projectId: number,
  write: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: write,
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({
          queryKey: planningKeys.one(firmId, projectId),
        }),
        queryClient.invalidateQueries({
          queryKey: takeoffKeys.one(firmId, projectId),
        }),
      ]),
  });
}

/** Loads a task onto the work. */
export function useCreateTask(firmId: number, projectId: number) {
  return usePlanningWrite(firmId, projectId, (payload: TaskWrite) =>
    createTask(firmId, projectId, payload),
  );
}

/** Saves the edit form of one task. */
export function useUpdateTask(firmId: number, projectId: number) {
  return usePlanningWrite(
    firmId,
    projectId,
    (variables: { taskId: number; payload: TaskWrite }) =>
      updateTask(firmId, projectId, variables.taskId, variables.payload),
  );
}

/** Removes one task from the planning. */
export function useRemoveTask(firmId: number, projectId: number) {
  return usePlanningWrite(firmId, projectId, (taskId: number) =>
    removeTask(firmId, projectId, taskId),
  );
}

/** Changes a task's status by one of the six actions. */
export function useTransitionTask(firmId: number, projectId: number) {
  return usePlanningWrite(
    firmId,
    projectId,
    (variables: { taskId: number; payload: TaskTransition }) =>
      transitionTask(firmId, projectId, variables.taskId, variables.payload),
  );
}

/** Corrects the actual dates of one task. */
export function useUpdateTaskActualDates(firmId: number, projectId: number) {
  return usePlanningWrite(
    firmId,
    projectId,
    (variables: { taskId: number; payload: TaskActualDates }) =>
      updateTaskActualDates(
        firmId,
        projectId,
        variables.taskId,
        variables.payload,
      ),
  );
}

/** Replaces the take-off lines of one task. */
export function useSetTaskLines(firmId: number, projectId: number) {
  return usePlanningWrite(
    firmId,
    projectId,
    (variables: { taskId: number; lineIds: number[] }) =>
      setTaskLines(firmId, projectId, variables.taskId, variables.lineIds),
  );
}

/** Records how much of one task is done. */
export function useSetTaskProgress(firmId: number, projectId: number) {
  return usePlanningWrite(
    firmId,
    projectId,
    (variables: { taskId: number; progressPercent: number }) =>
      setTaskProgress(
        firmId,
        projectId,
        variables.taskId,
        variables.progressPercent,
      ),
  );
}
