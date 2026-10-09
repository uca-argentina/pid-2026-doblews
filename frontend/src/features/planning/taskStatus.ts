import type { TaskAction, TaskStatus } from "./types";

/** How each status and action reads on screen, and which actions a status
 * allows.
 *
 * A .ts file with no components, like lineForm.ts: react-refresh can only
 * hot-reload files that export components alone. */

export const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "Pendiente",
  in_progress: "En curso",
  paused: "Pausada",
  finished: "Finalizada",
};

/** Mantine colours, not meanings: grey for what has not begun, the app's
 * green for what is moving, yellow for what is stopped, blue for what is done. */
export const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: "gray",
  in_progress: "obra",
  paused: "yellow",
  finished: "blue",
};

export const ACTION_LABELS: Record<TaskAction, string> = {
  start: "Iniciar",
  pause: "Pausar",
  resume: "Reanudar",
  finish: "Finalizar",
  reopen: "Reabrir",
  undo_start: "Deshacer inicio",
};

/** The diagram of ADR-009 section 5, from the screen's side: what can be done
 * to a task in each status, in the order the status menu lists them — the
 * usual next step first.
 *
 * The backend holds the same table and is the one that decides: this only
 * keeps the screen from offering an action that would come back as a 409. */
export const ACTIONS_BY_STATUS: Record<TaskStatus, TaskAction[]> = {
  pending: ["start"],
  in_progress: ["finish", "pause", "undo_start"],
  paused: ["resume"],
  finished: ["reopen"],
};

/** The actions that record a date, and so ask for one before running. */
export function recordsDate(action: TaskAction): boolean {
  return action === "start" || action === "finish";
}
