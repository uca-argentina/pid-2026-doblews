// Mirrors backend/app/schemas/dashboard.py field for field, in the wire's own
// snake_case like every other types.ts here. Money arrives as a decimal string
// and dates as "YYYY-MM-DD"; a month is the date of its first day.

import type { WorkProgressOut } from "../planning/types";

/** The work's first saved budget, v1 (D-17). */
export interface OriginalBudgetOut {
  version_number: number;
  note: string | null;
  total: string;
  created_at: string;
}

/** The original budget against the live one. Everything but the live total
 * is null while the work has no saved budget. */
export interface BudgetComparisonOut {
  original: OriginalBudgetOut | null;
  /** The budget tab's total, at today's reference prices. */
  updated_total: string;
  prices_as_of: string | null;
  /** updated minus original: positive is over. */
  difference: string | null;
  /** One decimal, e.g. "12.5". null when the original is zero. */
  difference_percent: string | null;
  direction: "above" | "below" | "equal" | null;
}

/** The whole work's progress against its fixed planning (HU-16). */
export interface ProgressBlockOut {
  /** null with no fixed planning, or no task left from it. */
  progress: WorkProgressOut | null;
  project_start_date: string | null;
  planned_end_date: string | null;
  baseline_end_date: string | null;
  /** Working days the planned end is past the fixed one; negative is ahead. */
  end_delay_days: number | null;
  /** Tasks past their fixed end and not finished: the Avance tab's own
   * "atrasada". Zero without a fixed planning. */
  overdue_tasks: number;
  has_tasks: boolean;
}

export interface MonthOut {
  /** The first day of the month. */
  month: string;
  amount: string;
  /** Before the month of today. */
  is_past: boolean;
}

/** What the work is expected to spend each month (D-18). months is empty
 * when there is nothing dated to project. */
export interface ProjectionOut {
  months: MonthOut[];
  projected_total: string;
  /** The take-off assigned to no task: shown apart, never spread. */
  unassigned_cost: string;
}

/** GET .../projects/{projectId}/dashboard. */
export interface DashboardOut {
  budget: BudgetComparisonOut;
  progress: ProgressBlockOut;
  projection: ProjectionOut;
  currency: string;
}
