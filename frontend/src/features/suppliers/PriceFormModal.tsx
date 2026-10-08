import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatMoney, matchesSearch } from "../../lib/format";
import { useResources } from "../catalog/useCatalog";
import type { UnitRef } from "../catalog/types";
import { useCurrentFirm } from "../firms/firmContext";
import {
  emptyPrice,
  pricePayload,
  priceValidation,
  type PriceValues,
} from "./supplierForm";
import { useAddPrice, useUpdatePrice } from "./useSuppliers";
import type { SupplierPriceOut } from "./types";

interface PriceFormModalProps {
  opened: boolean;
  supplierId: number;
  /** The row being edited, or null to add a material to the list. */
  price: SupplierPriceOut | null;
  /** Materials this supplier already lists: they are not offered again, since a
   * supplier does not repeat a material (ADR-010 section 2). */
  listedResourceIds: number[];
  onClose: () => void;
}

/** HU-17's add and edit of one row of a supplier's list.
 *
 * Adding picks a material from the catalogue and says what this supplier
 * charges; editing changes only the amounts, because the material is what
 * identifies the row. To price another one, remove the row and add the other. */
export function PriceFormModal({
  opened,
  supplierId,
  price,
  listedResourceIds,
  onClose,
}: PriceFormModalProps) {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={price ? "Editar precio" : "Agregar material"}
      centered
    >
      {/* Mounted per opening, so every open starts from the right values. */}
      {opened && (
        <PriceForm
          supplierId={supplierId}
          price={price}
          listedResourceIds={listedResourceIds}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

/** What the form needs to know about the material it is pricing. */
interface MaterialInfo {
  name: string;
  unit: UnitRef;
  reference_price: string;
  currency: string;
}

function PriceForm({
  supplierId,
  price,
  listedResourceIds,
  onClose,
}: Omit<PriceFormModalProps, "opened">) {
  const { firm } = useCurrentFirm();
  const resources = useResources(firm.id);
  const add = useAddPrice(firm.id, supplierId);
  const update = useUpdatePrice(firm.id, supplierId);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const pending = add.isPending || update.isPending;

  const form = useForm<PriceValues>({
    initialValues: price
      ? {
          resource_id: String(price.resource.id),
          unit_price: Number(price.unit_price),
          shipping_cost: Number(price.shipping_cost),
        }
      : emptyPrice,
    validate: {
      ...priceValidation,
      resource_id: (value) => (value ? null : "Elegí un material"),
    },
  });

  // Materials only: a supplier's list does not carry labour or equipment
  // (ADR-010 section 7), and the ones it already lists are not offered again.
  const options = (resources.data ?? [])
    .filter(
      (resource) =>
        resource.type === "material" &&
        !listedResourceIds.includes(resource.id),
    )
    .map((resource) => ({
      value: String(resource.id),
      label: `${resource.name} (${resource.unit.abbreviation})`,
    }));

  const material: MaterialInfo | undefined = price
    ? {
        name: price.resource.name,
        unit: price.resource.unit,
        reference_price: price.resource.reference_price,
        currency: price.currency,
      }
    : resources.data?.find(
        (resource) => String(resource.id) === form.values.resource_id,
      );

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      if (price) {
        await update.mutateAsync({
          priceId: price.id,
          payload: pricePayload(values),
        });
      } else {
        await add.mutateAsync({
          resource_id: Number(values.resource_id),
          ...pricePayload(values),
        });
      }
      notifications.show({
        title: price ? "Precio actualizado" : "Material agregado",
        message: material?.name ?? "La lista del proveedor se actualizó.",
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect is a material already in the list, added from
      // another tab; its text is the backend's.
      setSubmitError(apiErrorMessage(error, "No pudimos guardar el precio."));
    }
  });

  const unitLabel = material ? `por ${material.unit.abbreviation}` : undefined;

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        {price ? (
          <div>
            <Text size="sm" c="dimmed">
              Material
            </Text>
            <Text fw={600}>{price.resource.name}</Text>
          </div>
        ) : (
          <Select
            label="Material"
            placeholder={resources.isLoading ? "Cargando…" : "Buscar material"}
            data={options}
            searchable
            // Same search as the catalogue's: accent- and case-insensitive,
            // every word typed has to appear.
            filter={({ options: items, search }) =>
              items.filter(
                (item) => "label" in item && matchesSearch(item.label, search),
              )
            }
            nothingFoundMessage="Ningún material coincide"
            disabled={resources.isLoading || resources.isError}
            error={
              resources.isError ? "No pudimos cargar los materiales" : undefined
            }
            data-autofocus
            {...form.getInputProps("resource_id")}
          />
        )}

        {material && (
          <Text size="sm" c="dimmed">
            Precio de referencia (el del presupuesto):{" "}
            {formatMoney(material.reference_price, material.currency)}{" "}
            {unitLabel}
          </Text>
        )}

        <NumberInput
          label="Precio de este proveedor"
          description={
            material
              ? `Por una ${material.unit.abbreviation}, en la unidad del catálogo.`
              : "Por una unidad del material, en la unidad del catálogo."
          }
          placeholder="0"
          prefix="$ "
          decimalScale={2}
          decimalSeparator=","
          thousandSeparator="."
          allowNegative={false}
          hideControls
          inputMode="decimal"
          {...form.getInputProps("unit_price")}
        />

        <NumberInput
          label="Costo de envío"
          description="Un importe fijo por este material, sin importar la cantidad. 0 si no cobra."
          placeholder="0"
          prefix="$ "
          decimalScale={2}
          decimalSeparator=","
          thousandSeparator="."
          allowNegative={false}
          hideControls
          inputMode="decimal"
          {...form.getInputProps("shipping_cost")}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={pending}>
            Cancelar
          </Button>
          <Button type="submit" loading={pending}>
            {price ? "Guardar" : "Agregar"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
