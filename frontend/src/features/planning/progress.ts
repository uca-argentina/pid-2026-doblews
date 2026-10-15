import { EMPTY } from "../projects/projectFields";
import type { TaskOut } from "./types";

/** How the progress of HU-16 reads on its screen.
 *
 * A .ts file with no components, like taskStatus.ts: react-refresh can only
 * hot-reload files that export components alone. */

/** Whether a task is late, as the progress screen says it (HU-16): the end
 * fixed for it has passed and it is not finished.
 *
 * Deliberately not the backend's standing, which calls a task behind as soon
 * as its progress falls short of an even pace. That reads as an alarm for a
 * task still inside its dates; a date that has passed is one nobody argues
 * with. `today` is "YYYY-MM-DD" like the dates, so they compare as text. */
export function isOverdue(task: TaskOut, today: string): boolean {
  return (
    task.baseline_end_date !== null &&
    task.status !== "finished" &&
    task.baseline_end_date < today
  );
}

/** Only a task under way takes a progress: a pending one is at 0% and a
 * finished one at 100% (ADR-009 13). */
export function takesProgress(task: TaskOut): boolean {
  return task.status === "in_progress" || task.status === "paused";
}

/** What a task was planned to have done by today, or a dash without a
 * baseline to measure against. */
export function formatPlanned(task: TaskOut): string {
  return task.planned_progress_percent === null
    ? EMPTY
    : `${task.planned_progress_percent}%`;
}
