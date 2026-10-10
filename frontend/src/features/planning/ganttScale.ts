/** Where things fall on the Gantt's time axis (HU-15): which days it covers,
 * how wide a day is at each scale, what the header says and where a task's
 * bar starts and ends.
 *
 * A .ts file with no components, like taskStatus.ts: nothing here draws.
 *
 * Dates are handled as day numbers — whole days since 1970-01-01 — and not as
 * Date or dayjs objects. The API sends calendar dates with no instant attached
 * ("YYYY-MM-DD"), and what the axis needs from them is subtraction: a bar is
 * "this many days from the left edge, this many days long". Counting in UTC
 * keeps every day exactly one apart, where local midnights are 23 or 25 hours
 * apart across a clock change. */

import type { TaskOut } from "./types";

const MS_PER_DAY = 86_400_000;

/** The three zoom levels of the view. */
export type GanttScale = "day" | "week" | "month";

/** How many pixels one day takes at each scale. */
export const DAY_WIDTH: Record<GanttScale, number> = {
  day: 36,
  week: 14,
  month: 4,
};

const MONTHS = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

/** "2026-10-15" as a day number. */
export function toDay(value: string): number {
  const [year, month, date] = value.split("-").map(Number);
  return Date.UTC(year, month - 1, date) / MS_PER_DAY;
}

/** Today, by the clock of whoever is looking, as a day number. */
export function todayDay(): number {
  const now = new Date();
  return (
    Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / MS_PER_DAY
  );
}

function partsOf(day: number) {
  const date = new Date(day * MS_PER_DAY);
  return {
    year: date.getUTCFullYear(),
    month: date.getUTCMonth(),
    date: date.getUTCDate(),
    /** 0 is Sunday, as in Date. */
    weekday: date.getUTCDay(),
  };
}

function mondayOf(day: number): number {
  return day - ((partsOf(day).weekday + 6) % 7);
}

/** The days the axis covers: `days` of them, the first being `start`. */
export interface GanttRange {
  start: number;
  days: number;
}

/** Everything there is to show, with room around it: from the week before the
 * earliest date to the week after the latest, in whole weeks so the axis
 * starts on a Monday at every scale.
 *
 * Today is always inside, even for a work that ended or has not begun: it is
 * what the view opens on. */
export function ganttRange(
  tasks: TaskOut[],
  projectStartDate: string | null,
  plannedEndDate: string | null,
  today: number,
): GanttRange {
  const dates = [projectStartDate, plannedEndDate];
  for (const task of tasks) {
    dates.push(task.planned_start_date, task.planned_end_date);
  }
  const days = [today];
  for (const date of dates) {
    if (date !== null) days.push(toDay(date));
  }

  const start = mondayOf(Math.min(...days)) - 7;
  const end = mondayOf(Math.max(...days)) + 14;
  return { start, days: end - start };
}

/** The same range, made longer when it would not fill the screen: a short
 * work on a wide window would otherwise end in a blank stretch with no grid.
 * It grows to the right, by whole weeks, and never shrinks. */
export function atLeast(range: GanttRange, days: number): GanttRange {
  if (days <= range.days) return range;
  return { start: range.start, days: Math.ceil(days / 7) * 7 };
}

/** A stretch of the axis: `days` long, `offset` days from its left edge. */
export interface GanttSpan {
  offset: number;
  days: number;
}

/** A task's bar: from its start to its end, both included, so a task of one
 * day is one day wide (ADR-009 section 4, "fin inclusivo").
 *
 * The planned dates are the ones to read: once a task started or finished
 * they are its actual ones. null while the work has no start date, when
 * nothing has dates to draw. */
export function ganttBar(task: TaskOut, range: GanttRange): GanttSpan | null {
  if (task.planned_start_date === null || task.planned_end_date === null) {
    return null;
  }
  const start = toDay(task.planned_start_date);
  const end = toDay(task.planned_end_date);
  return { offset: start - range.start, days: end - start + 1 };
}

/** One cell of the header: a day, a week, a month or a year. */
export interface GanttCell extends GanttSpan {
  label: string;
}

type Unit = "day" | "week" | "month" | "year";

/** The first day of the unit after the one `day` is in. */
function nextBoundary(day: number, unit: Unit): number {
  const { year, month } = partsOf(day);
  switch (unit) {
    case "day":
      return day + 1;
    case "week":
      return mondayOf(day) + 7;
    case "month":
      return Date.UTC(year, month + 1, 1) / MS_PER_DAY;
    case "year":
      return Date.UTC(year + 1, 0, 1) / MS_PER_DAY;
  }
}

/** The range cut into cells of one unit. The first and the last are clipped
 * to the range, since it starts and ends on a week and not on a month. */
function cells(
  range: GanttRange,
  unit: Unit,
  label: (day: number) => string,
): GanttCell[] {
  const end = range.start + range.days;
  const result: GanttCell[] = [];
  let day = range.start;
  while (day < end) {
    const next = Math.min(nextBoundary(day, unit), end);
    result.push({
      offset: day - range.start,
      days: next - day,
      label: label(day),
    });
    day = next;
  }
  return result;
}

/** The two rows of the header. The bottom one is the scale itself — days,
 * weeks named by their Monday, or months — and the top one says where those
 * fall: in which month, or in which year. */
export function ganttHeader(
  range: GanttRange,
  scale: GanttScale,
): { top: GanttCell[]; bottom: GanttCell[] } {
  const monthAndYear = (day: number) => {
    const { year, month } = partsOf(day);
    return `${MONTHS[month]} ${year}`;
  };
  const dayOfMonth = (day: number) => String(partsOf(day).date);

  if (scale === "month") {
    return {
      top: cells(range, "year", (day) => String(partsOf(day).year)),
      bottom: cells(range, "month", (day) => MONTHS[partsOf(day).month]),
    };
  }
  return {
    top: cells(range, "month", monthAndYear),
    bottom: cells(range, scale, dayOfMonth),
  };
}
