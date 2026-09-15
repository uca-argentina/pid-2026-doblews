/** Validation for the fields that describe a person's account, shared by every
 * form that creates one or sets a password for someone else: the roster add
 * (HU-2), and the firm creation and password reset of support (HU-7).
 *
 * The same rules the backend enforces in schemas/member.py (Email and
 * TypedPassword), so the usual mistakes are caught before a round trip. They
 * are not the protection: the API validates every field again, and this only
 * spares the user a 422 whose English field errors would not help them.
 *
 * Each returns the message to show, or null when the value is fine, which is
 * the shape @mantine/form's validate expects. */

// Same limit as account.name and firm.name.
export const MAX_NAME = 120;
export const MIN_PASSWORD = 8;
// bcrypt ignores anything past the 72nd byte, so the backend refuses longer
// passwords. Counted in bytes and not characters for the same reason: "ñ" is
// two bytes, so 40 of them are already past the limit.
export const MAX_PASSWORD_BYTES = 72;

export function validateName(value: string): string | null {
  const name = value.trim();
  if (name.length === 0) return "Ingresá el nombre";
  return name.length <= MAX_NAME ? null : `Como máximo ${MAX_NAME} caracteres`;
}

export function validateEmail(value: string): string | null {
  return /^\S+@\S+\.\S+$/.test(value.trim()) ? null : "Ingresá un email válido";
}

export function validatePassword(value: string): string | null {
  if (value.length < MIN_PASSWORD) return `Al menos ${MIN_PASSWORD} caracteres`;
  const bytes = new TextEncoder().encode(value).length;
  return bytes <= MAX_PASSWORD_BYTES
    ? null
    : "La contraseña es demasiado larga";
}
