/** How numbers and searches read to someone here: es-AR conventions. */

const moneyFormatters = new Map<string, Intl.NumberFormat>();

/** A decimal string from the API as money: "16000.00" → "$ 16.000,00".
 *
 * Converting to Number only at the last step, for display, is safe: a
 * NUMERIC(14,2) fits well inside a double's exact integer range, and nothing
 * computed from the result goes back to the server. One formatter per
 * currency, built once, because constructing Intl.NumberFormat is not cheap
 * and a listing calls this per row. */
export function formatMoney(amount: string, currency: string): string {
  let formatter = moneyFormatters.get(currency);
  if (!formatter) {
    formatter = new Intl.NumberFormat("es-AR", { style: "currency", currency });
    moneyFormatters.set(currency, formatter);
  }
  return formatter.format(Number(amount));
}

const quantityFormatter = new Intl.NumberFormat("es-AR", {
  maximumFractionDigits: 4,
});

/** A decimal string from the API as a quantity, without the padding the
 * column's scale adds: "60.0000" → "60", "0.2500" → "0,25", "0.0470" →
 * "0,047". */
export function formatQuantity(value: string): string {
  return quantityFormatter.format(Number(value));
}

/** Lowercased and without diacritics, so "común" and "comun" compare equal. */
function normalize(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/** Whether a name answers a search box: case- and accent-insensitive, and
 * every word typed has to appear somewhere, in any order — "pared 15" finds
 * "Pared de ladrillo común 15cm". An empty search matches everything. */
export function matchesSearch(text: string, query: string): boolean {
  const haystack = normalize(text);
  return normalize(query)
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}
