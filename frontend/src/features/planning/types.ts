// Mirrors backend/app/schemas/task.py field for field, in the wire's own
// snake_case like every other types.ts here. Money arrives as a decimal string
// ("2908350.00") and stays one until lib/format.ts prints it; dates arrive as
// "YYYY-MM-DD", calendar dates with no instant attached.

/** The four states a task can be in (ADR-009 section 5). */
export type TaskStatus = "pending" | "in_progress" | "paused" | "finished";

/** The six things that can be done to a task's status, and nothing else. */
export type TaskAction =
  "start" | "pause" | "resume" | "finish" | "reopen" | "undo_start";

/** Someone who answers for a task, or who may be picked to. */
export interface AssigneeOut {
  account_id: number;
  name: string;
}

/** One task, as the planning lists it and every write answers with. */
export interface TaskOut {
  id: number;
  name: string;
  description: string | null;
  /** Working days, Monday to Friday. */
  estimated_duration_days: number;
  /** "No antes de": the earliest day the task may be planned to start. */
  not_before_date: string | null;
  status: TaskStatus;
  assignee: AssigneeOut | null;
  /** Recorded by starting the task. null while it is pending. */
  actual_start_date: string | null;
  /** Recorded by finishing it. null unless it is finished. */
  actual_end_date: string | null;
  /** What its take-off lines cost at today's prices: "0.00" with none. null
   * when the caller may not see costs — the project client (ADR-009 9). */
  cost: string | null;
}

/** GET .../projects/{projectId}/tasks: the tasks and what they add up to, in
 * one answer so the list and the totals never disagree on screen. */
export interface PlanningOut {
  tasks: TaskOut[];
  /** What the take-off lines assigned to no task cost. */
  unassigned_cost: string | null;
  /** The tasks' costs plus the unassigned amount, as shown. null when the
   * caller may not see costs — which is what the screen asks before rendering
   * any cost at all. It may differ by cents from the budget's total, which
   * rounds per resource (ADR-009 section 8). */
  total_cost: string | null;
  currency: string;
}

/** The add and edit form: the whole editable state of a task, sent every time
 * (the edit is a PUT), so null means empty in both directions. */
export interface TaskWrite {
  name: string;
  description: string | null;
  estimated_duration_days: number;
  not_before_date: string | null;
  assignee_account_id: number | null;
}

/** One action on a task's status. on_date is only read by "start" and
 * "finish", which record a date; left out, the backend uses today. */
export interface TaskTransition {
  action: TaskAction;
  on_date?: string | null;
}

/** The correction form for the dates a transition recorded. Both keys are
 * always sent; which of them a task may carry depends on its status. */
export interface TaskActualDates {
  actual_start_date: string | null;
  actual_end_date: string | null;
}
