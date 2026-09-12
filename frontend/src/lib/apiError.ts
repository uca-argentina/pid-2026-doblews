import { isAxiosError } from "axios";

/** Shown when the request never reached the backend. Also used by the login
 * screen, so the two cannot drift apart. */
export const CONNECTION_ERROR =
  "No pudimos conectar con el servidor. Probá de nuevo en otro momento.";

/** What to show the user when a call fails.
 *
 * A 409 is the only status whose body is worth rendering: the roster endpoints
 * answer one with a `detail` written for the person reading it ("Esta persona
 * ya es miembro del estudio", "Transferí esa responsabilidad antes de darla de
 * baja"). Passing it through is what keeps those texts in one place — the
 * backend, where the rule lives — instead of a copy here that has to be kept in
 * sync with it.
 *
 * Everything else gets the caller's own fallback:
 * - 403 and 404 mean the screen is showing something the backend disagrees
 *   with, which is a stale list rather than anything the user did;
 * - 422 is a body the form should have caught, so its English field errors
 *   would only confuse;
 * - a 401 never gets here: the interceptor in lib/api.ts already ended the
 *   session and the app is on its way to the login. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) {
    return fallback;
  }

  if (!error.response) {
    return CONNECTION_ERROR;
  }

  const detail = (error.response.data as { detail?: unknown } | undefined)
    ?.detail;
  if (error.response.status === 409 && typeof detail === "string") {
    return detail;
  }

  return fallback;
}
