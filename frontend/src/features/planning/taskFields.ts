/** How a task's plain fields are printed, shared by the table and the card. */

/** A duration in working days: 1 → "1 día", 10 → "10 días". The column and
 * the card label say they are working days, so each value does not repeat it. */
export function formatDuration(days: number): string {
  return days === 1 ? "1 día" : `${days} días`;
}
