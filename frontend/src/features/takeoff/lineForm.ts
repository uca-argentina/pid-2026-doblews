/** The form state of a take-off line, shared by the add and edit modals.
 *
 * In a .ts file apart from LineFields.tsx because react-refresh can only
 * hot-reload files that export components alone. */

// The limits the backend enforces: NUMERIC(14,3) with CHECK > 0, and a 150
// character note. Checked here to spare a round trip and a 422 whose English
// field errors would not help; the API checks them again regardless.
const MAX_NOTE = 150;
const MAX_QUANTITY = 99_999_999_999.999;

/** The two editable fields of a line, as the form holds them. NumberInput
 * speaks number, or string while the value is empty or half typed. */
export interface LineValues {
  quantity: number | string;
  note: string;
}

export const emptyLine: LineValues = { quantity: "", note: "" };

export const lineValidation = {
  quantity: (value: number | string) => {
    if (value === "") return "Ingresá la cantidad";
    const quantity = Number(value);
    if (!Number.isFinite(quantity) || quantity <= 0) {
      return "La cantidad tiene que ser mayor que cero";
    }
    return quantity <= MAX_QUANTITY ? null : "La cantidad es demasiado grande";
  },
  note: (value: string) =>
    value.trim().length <= MAX_NOTE
      ? null
      : `Como máximo ${MAX_NOTE} caracteres`,
};

/** The payload half both writes share: quantity as a decimal string and an
 * empty note as null, which is what makes the edit clear a note on purpose.
 *
 * String(Number(...)) and not the raw value: the input is limited to three
 * decimals, so the number printed back is exactly what was typed ("12.5"),
 * with a dot whatever the separator on screen. */
export function linePayload(values: LineValues) {
  return {
    quantity: String(Number(values.quantity)),
    note: values.note.trim() || null,
  };
}
