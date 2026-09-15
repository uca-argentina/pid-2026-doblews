import { isAxiosError } from "axios";

/** Shown when the request never reached the backend. Also used by the login
 * screen, so the two cannot drift apart. */
export const CONNECTION_ERROR =
  "No pudimos conectar con el servidor. Probá de nuevo en otro momento.";

/** What to show the user when a call fails.
 *
 * A 409 is a status whose body is worth rendering: the roster endpoints
 * answer one with a `detail` written for the person reading it ("Esta persona
 * ya es miembro del estudio", "Transferí esa responsabilidad antes de darla de
 * baja"). Passing it through is what keeps those texts in one place — the
 * backend, where the rule lives — instead of a copy here that has to be kept in
 * sync with it.
 *
 * A 422 gets the same treatment only when its detail is a string. The
 * catalogue admin screens (HU-8) raise a 422 of their own for a malformed
 * reference — an inactive unit or material — with a hand-written detail meant
 * to be shown as is, exactly like a 409. A standard FastAPI/Pydantic 422 (a
 * form field the client should have already caught) carries detail as an
 * *array* of field errors, never a string, so this can never accidentally
 * surface one of those.
 *
 * Everything else gets the caller's own fallback:
 * - 403 and 404 mean the screen is showing something the backend disagrees
 *   with, which is a stale list rather than anything the user did;
 * - a 401 never gets here: the interceptor in lib/api.ts already ended the
 *   session and the app is on its way to the login. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) {
    return fallback;
  }

  if (!error.response) {
    return CONNECTION_ERROR;
  }

  const { status } = error.response;
  const detail = (error.response.data as { detail?: unknown } | undefined)
    ?.detail;
  if ((status === 409 || status === 422) && typeof detail === "string") {
    return detail;
  }

  return fallback;
}
