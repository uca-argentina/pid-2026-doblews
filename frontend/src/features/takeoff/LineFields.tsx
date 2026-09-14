import { NumberInput, TextInput } from "@mantine/core";
import type { UseFormReturnType } from "@mantine/form";
import type { LineValues } from "./lineForm";

interface LineFieldsProps {
  form: UseFormReturnType<LineValues>;
  /** The recipe's unit, shown beside the quantity: it is the unit being typed
   * in, and there is no other to choose. */
  unit: string;
}

/** Quantity and note, shared by the add and edit forms of a line.
 *
 * The quantity is typed the way it is read here — comma for decimals, dot for
 * thousands — and limited to three decimals, the scale the take-off is stored
 * at, so what is typed is never silently rounded. */
export function LineFields({ form, unit }: LineFieldsProps) {
  return (
    <>
      <NumberInput
        label="Cantidad"
        placeholder="0"
        rightSection={unit}
        rightSectionWidth={48}
        decimalScale={3}
        decimalSeparator=","
        thousandSeparator="."
        allowNegative={false}
        hideControls
        inputMode="decimal"
        {...form.getInputProps("quantity")}
      />
      <TextInput
        label="Nota"
        description="Opcional. Sirve para distinguir dos líneas de la misma receta."
        placeholder="planta baja, sector A…"
        {...form.getInputProps("note")}
      />
    </>
  );
}
