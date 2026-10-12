import type { ProgressStanding } from "./types";

/** How the comparison of HU-16 reads on screen.
 *
 * A .ts file with no components, like taskStatus.ts: react-refresh can only
 * hot-reload files that export components alone. */

export const STANDING_LABELS: Record<ProgressStanding, string> = {
  behind: "Atrasada",
  on_track: "En fecha",
  ahead: "Adelantada",
};

/** Mantine colours. Red for what needs attention, as for a critical task;
 * the app's green for what is going as planned; blue for what is ahead. */
export const STANDING_COLORS: Record<ProgressStanding, string> = {
  behind: "red",
  on_track: "obra",
  ahead: "blue",
};

/** The gap in points, with its sign: "−13", "+8", "0". A real minus sign and
 * not a hyphen, so it lines up with the plus. */
export function formatGap(gap: number): string {
  if (gap === 0) return "0";
  return gap > 0 ? `+${gap}` : `−${Math.abs(gap)}`;
}

/** The gap as a phrase, where nothing around it says what the number is:
 * "13 puntos por debajo", "1 punto por encima", "Sin diferencia". */
export function describeGap(gap: number): string {
  if (gap === 0) return "Sin diferencia";
  const points = Math.abs(gap) === 1 ? "1 punto" : `${Math.abs(gap)} puntos`;
  return `${points} ${gap > 0 ? "por encima" : "por debajo"}`;
}
