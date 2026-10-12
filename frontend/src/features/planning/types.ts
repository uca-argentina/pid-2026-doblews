// Mirrors backend/app/schemas/task.py field for field, in the wire's own
// snake_case like every other types.ts here. Money arrives as a decimal string
// ("2908350.00") and stays one until lib/format.ts prints it; dates arrive as
// "YYYY-MM-DD", calendar dates with no instant attached.

/** The four states a task can be in (ADR-009 section 5). */
export type TaskStatus = "pending" | "in_progress" | "paused" | "finished";

/** The six things that can be done to a task's status, and nothing else. */
/** How the actual progress compares with the planned one (HU-16): more than
 * five points under it, within five, or more than five over. */
export type ProgressStanding = "behind" | "on_track" | "ahead";

export type TaskAction =
  "start" | "pause" | "resume" | "finish" | "reopen" | "undo_start";

/** Someone who answers for a task, or who may be picked to. */
export interface AssigneeOut {
  account_id: number;
  name: string;
}

/** Another task, as a dependency names it: enough to say whether it is done. */
export interface TaskRefOut {
  id: number;
  name: string;
  status: TaskStatus;
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
  /** How much of it is done, as last recorded: a whole number from 0 to 100.
   * Always 0 while pending and 100 once finished (ADR-009 13). */
  progress_percent: number;
  /** The planned dates as they were when the planning was last fixed. null on
   * a task loaded since, which is out of the comparison until it is fixed
   * again. */
  baseline_start_date: string | null;
  baseline_end_date: string | null;
  /** What it was planned to have done by today, against that baseline; the
   * actual progress minus it, so negative is behind; and which of the three
   * that makes it. All null without a baseline. */
  planned_progress_percent: number | null;
  progress_gap: number | null;
  progress_standing: ProgressStanding | null;
  /** What its take-off lines cost at today's prices: "0.00" with none. null
   * when the caller may not see costs — the project client (ADR-009 9). */
  cost: string | null;
  /** Computed on every read (HU-14), and null while the work has no start
   * date. Once the task started this is its actual start, and once it
   * finished both are its actual dates: what happened replaces the plan. */
  planned_start_date: string | null;
  planned_end_date: string | null;
  /** Working days it may slip without moving the end of the work. null once
   * finished, or with no start date. */
  slack_days: number | null;
  /** Slack zero: a delay here is a delay of the work. */
  is_critical: boolean;
  /** What it waits for and what waits for it, each with its status. */
  predecessors: TaskRefOut[];
  successors: TaskRefOut[];
}

/** The progress of the whole work against its fixed planning (HU-16): each
 * task weighs its estimated duration, and only those with a baseline count. */
export interface WorkProgressOut {
  actual_percent: number;
  planned_percent: number;
  gap: number;
  standing: ProgressStanding;
}

/** GET .../projects/{projectId}/tasks: the tasks and what they add up to, in
 * one answer so the list and the unassigned amount never disagree on screen. */
export interface PlanningOut {
  /** In planned order: by planned start, then in the order they were loaded. */
  tasks: TaskOut[];
  /** The work's start date, which every planned date counts from. null means
   * the screen asks for it. */
  project_start_date: string | null;
  /** When the work is planned to end: the latest planned end of its tasks. */
  planned_end_date: string | null;
  /** The day the planning was last fixed, and when the work was planned to
   * end that day. Both null means the screen asks to fix it. */
  baseline_set_on: string | null;
  baseline_end_date: string | null;
  /** null until the planning is fixed. */
  progress: WorkProgressOut | null;
  /** What the take-off lines assigned to no task cost. */
  unassigned_cost: string | null;
  /** The tasks' costs plus the unassigned amount. Not shown: the work's total
   * is the take-off's to show. What the screen reads from it is whether it is
   * null, which is how the backend says the caller may not see costs. */
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
  /** Every task this one waits for. The list replaces the ones it had. */
  predecessor_ids: number[];
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
