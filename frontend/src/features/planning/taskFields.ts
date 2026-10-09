/** How a task's plain fields are printed, shared by the table, the card and
 * the detail. */

import { EMPTY, formatDate } from "../projects/projectFields";
import type { TaskOut } from "./types";

/** A duration in working days: 1 → "1 día", 10 → "10 días". The column and
 * the card label say they are working days, so each value does not repeat it. */
export function formatDuration(days: number): string {
  return days === 1 ? "1 día" : `${days} días`;
}

/** The same duration where nothing around it says the days are working
 * days: "1 día hábil", "10 días hábiles". */
export function formatWorkingDays(days: number): string {
  return days === 1 ? "1 día hábil" : `${days} días hábiles`;
}

/** One end of a task as the listing shows it: the planned date, which is the
 * actual one once it happened (HU-14). `actual` says which of the two it is,
 * so the screen can tell "this happened" from "this is expected". */
export interface TaskDate {
  label: string;
  actual: boolean;
}

export function taskStart(task: TaskOut): TaskDate {
  return task.actual_start_date
    ? { label: formatDate(task.actual_start_date), actual: true }
    : { label: formatDate(task.planned_start_date), actual: false };
}

export function taskEnd(task: TaskOut): TaskDate {
  return task.actual_end_date
    ? { label: formatDate(task.actual_end_date), actual: true }
    : { label: formatDate(task.planned_end_date), actual: false };
}

/** The slack in working days: "Crítica" at zero, "3 días" otherwise, and a
 * dash once finished or with nothing planned. */
export function formatSlack(task: TaskOut): string {
  if (task.slack_days === null) return EMPTY;
  if (task.is_critical) return "Crítica";
  return formatDuration(task.slack_days);
}

/** "«A»", "«A» y «B»", "«A», «B» y «C»": a list of tasks inside a sentence. */
export function joinTaskNames(names: string[]): string {
  const quoted = names.map((name) => `«${name}»`);
  if (quoted.length <= 1) return quoted.join("");
  return `${quoted.slice(0, -1).join(", ")} y ${quoted[quoted.length - 1]}`;
}

/** The predecessors still keeping a task from starting (HU-14). The backend
 * is the one that refuses; this only lets the screen say so beforehand. */
export function unfinishedPredecessors(task: TaskOut): string[] {
  return task.predecessors
    .filter((predecessor) => predecessor.status !== "finished")
    .map((predecessor) => predecessor.name);
}

/** Every task that waits for this one, directly or along a chain. Making any
 * of them a predecessor would close a cycle, so the form does not offer them:
 * the backend refuses it anyway, and a choice that fails is worse than none. */
export function dependentsOf(taskId: number, tasks: TaskOut[]): Set<number> {
  const byId = new Map(tasks.map((task) => [task.id, task]));
  const found = new Set<number>();
  const pending = [taskId];
  while (pending.length > 0) {
    const current = byId.get(pending.pop()!);
    for (const successor of current?.successors ?? []) {
      if (!found.has(successor.id)) {
        found.add(successor.id);
        pending.push(successor.id);
      }
    }
  }
  return found;
}

/** The successors of a task that already started: the ones reopening it
 * leaves running on top of unfinished work, which its confirmation names. */
export function startedSuccessors(task: TaskOut): string[] {
  return task.successors
    .filter((successor) => successor.status !== "pending")
    .map((successor) => successor.name);
}
