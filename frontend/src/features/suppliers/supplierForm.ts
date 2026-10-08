/** The form state of a supplier and of a price row, with the validation and
 * the payloads their modals share.
 *
 * In a .ts file apart from the modals because react-refresh can only hot-reload
 * files that export components alone.
 *
 * The limits are the backend's (app/schemas/supplier.py and the columns behind
 * it), checked here to spare a round trip and a 422 whose English field errors
 * would not help. The API checks them again regardless. */

import { validateEmail } from "../../lib/accountFields";
import type { SupplierOut, SupplierWrite } from "./types";

const MAX_NAME = 150;
const MAX_CONTACT_NAME = 120;
const MAX_PHONE = 30;
const MAX_ADDRESS = 255;
// The limit of NUMERIC(14,2).
const MAX_AMOUNT = 999_999_999_999.99;

export interface SupplierValues {
  name: string;
  contact_name: string;
  contact_email: string;
  phone: string;
  address: string;
}

export const emptySupplier: SupplierValues = {
  name: "",
  contact_name: "",
  contact_email: "",
  phone: "",
  address: "",
};

function maxLength(limit: number) {
  return (value: string) =>
    value.trim().length <= limit ? null : `Como máximo ${limit} caracteres`;
}

export const supplierValidation = {
  name: (value: string) =>
    value.trim().length === 0
      ? "Ingresá el nombre"
      : maxLength(MAX_NAME)(value),
  contact_name: maxLength(MAX_CONTACT_NAME),
  // Optional: an empty email is no email, so only a typed one is checked.
  contact_email: (value: string) =>
    value.trim() === "" ? null : validateEmail(value),
  phone: maxLength(MAX_PHONE),
  address: maxLength(MAX_ADDRESS),
};

/** What the form holds for an existing supplier. */
export function supplierToValues(supplier: SupplierOut): SupplierValues {
  return {
    name: supplier.name,
    contact_name: supplier.contact_name ?? "",
    contact_email: supplier.contact_email ?? "",
    phone: supplier.phone ?? "",
    address: supplier.address ?? "",
  };
}

/** An empty optional field leaves as null, which on an edit clears it. */
export function supplierPayload(values: SupplierValues): SupplierWrite {
  const optional = (value: string) => value.trim() || null;
  return {
    name: values.name.trim(),
    contact_name: optional(values.contact_name),
    contact_email: optional(values.contact_email),
    phone: optional(values.phone),
    address: optional(values.address),
  };
}

/** The fields of a price row, as the form holds them. NumberInput speaks
 * number, or string while the value is empty or half typed. */
export interface PriceValues {
  resource_id: string | null;
  unit_price: number | string;
  shipping_cost: number | string;
}

export const emptyPrice: PriceValues = {
  resource_id: null,
  unit_price: "",
  // Zero from the start: "sin costo de envío" is the common case, and an empty
  // field would otherwise have to be filled in just to say so.
  shipping_cost: 0,
};

function validateAmount(value: number | string, missing: string) {
  if (value === "") return missing;
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount < 0) {
    return "No puede ser negativo";
  }
  return amount <= MAX_AMOUNT ? null : "El importe es demasiado grande";
}

export const priceValidation = {
  unit_price: (value: number | string) =>
    validateAmount(value, "Ingresá el precio"),
  shipping_cost: (value: number | string) =>
    validateAmount(value, "Ingresá el envío (0 si no cobra)"),
};

/** Amounts as decimal strings: String(Number(...)) and not the raw value,
 * because the input is limited to two decimals, so the number printed back is
 * exactly what was typed, with a dot whatever the separator on screen. */
export function pricePayload(values: PriceValues) {
  return {
    unit_price: String(Number(values.unit_price)),
    shipping_cost: String(Number(values.shipping_cost)),
  };
}
