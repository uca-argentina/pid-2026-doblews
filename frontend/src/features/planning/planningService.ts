import { api } from "../../lib/api";
import type {
  AssigneeOut,
  PlanningOut,
  TaskActualDates,
  TaskOut,
  TaskTransition,
  TaskWrite,
} from "./types";

/** Every call the planning screen makes. One module so the URLs live in one
 * place, and the hooks in usePlanning.ts stay about caching. */

function tasksUrl(firmId: number, projectId: number): string {
  return `/firms/${firmId}/projects/${projectId}/tasks`;
}

/** The whole planning of a work: its tasks and — for those who may see it —
 * what each costs, what is left unassigned and the total. */
export async function fetchPlanning(
  firmId: number,
  projectId: number,
): Promise<PlanningOut> {
  const { data } = await api.get<PlanningOut>(tasksUrl(firmId, projectId));
  return data;
}

/** Who may be made responsible for a task: the options of the form's picker.
 * Only for those who may manage the planning; anyone else gets a 403. */
export async function fetchTaskAssignees(
  firmId: number,
  projectId: number,
): Promise<AssigneeOut[]> {
  const { data } = await api.get<AssigneeOut[]>(
    `${tasksUrl(firmId, projectId)}/assignees`,
  );
  return data;
}

/** Loads a task onto the work. A 409 means the name is taken or the assignee
 * may not be one, and its detail says which. */
export async function createTask(
  firmId: number,
  projectId: number,
  payload: TaskWrite,
): Promise<TaskOut> {
  const { data } = await api.post<TaskOut>(
    tasksUrl(firmId, projectId),
    payload,
  );
  return data;
}

/** A PUT: every field of the form is sent, so an empty one clears it. */
export async function updateTask(
  firmId: number,
  projectId: number,
  taskId: number,
  payload: TaskWrite,
): Promise<TaskOut> {
  const { data } = await api.put<TaskOut>(
    `${tasksUrl(firmId, projectId)}/${taskId}`,
    payload,
  );
  return data;
}

/** A logical removal: the API answers 204 and the task's take-off lines go
 * back to being unassigned. */
export async function removeTask(
  firmId: number,
  projectId: number,
  taskId: number,
): Promise<void> {
  await api.delete(`${tasksUrl(firmId, projectId)}/${taskId}`);
}

/** Starts, pauses, resumes, finishes or reopens a task, or undoes its start.
 * A 409 means the task's status does not allow that action. */
export async function transitionTask(
  firmId: number,
  projectId: number,
  taskId: number,
  payload: TaskTransition,
): Promise<TaskOut> {
  const { data } = await api.post<TaskOut>(
    `${tasksUrl(firmId, projectId)}/${taskId}/transitions`,
    payload,
  );
  return data;
}

/** Corrects the dates a transition recorded, without changing the status. */
export async function updateTaskActualDates(
  firmId: number,
  projectId: number,
  taskId: number,
  payload: TaskActualDates,
): Promise<TaskOut> {
  const { data } = await api.put<TaskOut>(
    `${tasksUrl(firmId, projectId)}/${taskId}/actual-dates`,
    payload,
  );
  return data;
}

/** Replaces the take-off lines of a task with exactly these. An empty list
 * gives them all back. */
export async function setTaskLines(
  firmId: number,
  projectId: number,
  taskId: number,
  lineIds: number[],
): Promise<TaskOut> {
  const { data } = await api.put<TaskOut>(
    `${tasksUrl(firmId, projectId)}/${taskId}/lines`,
    { line_ids: lineIds },
  );
  return data;
}

/** Records how much of a task is done, from 0 to 100. A 409 means its status
 * takes no progress: a pending task is at 0 and a finished one at 100. */
export async function setTaskProgress(
  firmId: number,
  projectId: number,
  taskId: number,
  progressPercent: number,
): Promise<TaskOut> {
  const { data } = await api.put<TaskOut>(
    `${tasksUrl(firmId, projectId)}/${taskId}/progress`,
    { progress_percent: progressPercent },
  );
  return data;
}

/** Fixes the planning: keeps today's planned dates as what the progress is
 * compared against, replacing any fixed before. Answers with the whole
 * planning, since every task changes. A 409 means the work has no start date
 * or no tasks. */
export async function fixBaseline(
  firmId: number,
  projectId: number,
): Promise<PlanningOut> {
  const { data } = await api.post<PlanningOut>(
    `${tasksUrl(firmId, projectId)}/baseline`,
  );
  return data;
}
