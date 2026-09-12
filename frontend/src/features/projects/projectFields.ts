import dayjs from "dayjs";

/** Shown where a work has left an optional field empty. A dash rather than an
 * empty cell, so a column reads as "nothing here" instead of as a broken
 * render. */
export const EMPTY = "—";

/** A calendar date as the listing and the detail print it.
 *
 * The API sends "YYYY-MM-DD", which is unambiguous to a machine and reads
 * backwards to anyone here, so it is shown as DD/MM/YYYY. No timezone is
 * involved on either side: "empieza el 15 de octubre" has no instant attached
 * (modelo-datos 3.6), which is why dayjs parses the plain string and never a
 * Date built from it. */
export function formatDate(value: string | null): string {
  if (!value) return EMPTY;
  const date = dayjs(value, "YYYY-MM-DD");
  return date.isValid() ? date.format("DD/MM/YYYY") : EMPTY;
}
