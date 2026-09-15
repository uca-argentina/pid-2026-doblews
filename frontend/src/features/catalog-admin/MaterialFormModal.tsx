import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Center,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useUnitsOfMeasure } from "../units-of-measure/useUnitsOfMeasure";
import type { UnitOfMeasureOut } from "../units-of-measure/types";
import { findUnitId } from "./unitLookup";
import { useCreateResource, useUpdateResource } from "./useCatalogAdmin";
import type { ResourceOut, ResourceType, ResourceWrite } from "./types";

// Same limit as resource.name (String(150)).
const MAX_NAME = 150;

const TYPE_OPTIONS: { value: ResourceType; label: string }[] = [
  { value: "material", label: "Material" },
  { value: "labor", label: "Mano de obra" },
  { value: "equipment", label: "Equipo" },
];

interface MaterialFormModalProps {
  opened: boolean;
  /** The material being edited, or null to create a new one. */
  resource: ResourceOut | null;
  onClose: () => void;
}

/** HU-8's create/edit form for one material.
 *
 * One form for both, like ProjectFormModal: the edit is a PUT that takes the
 * whole row, so there is no field only one of the two can touch.
 *
 * The inner form waits for the units of measure to load before mounting, not
 * just for the <Select> to be usable: ResourceOut.unit only carries {code,
 * abbreviation}, so an edit has to resolve that code back to an id via
 * findUnitId(units, code) once, at the moment the form's initialValues are
 * computed — mounting early would capture a still-null id and never revisit
 * it, since useForm's initialValues are read once per mount. */
export function MaterialFormModal({
  opened,
  resource,
  onClose,
}: MaterialFormModalProps) {
  const units = useUnitsOfMeasure();

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={resource ? `Editar ${resource.name}` : "Nuevo material"}
      centered
    >
      {opened &&
        (units.isLoading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : (
          <MaterialForm
            key={resource?.id ?? "new"}
            resource={resource}
            units={units.data ?? []}
            onClose={onClose}
          />
        ))}
    </Modal>
  );
}

interface FormValues {
  name: string;
  type: ResourceType | null;
  unit_of_measure_id: string | null;
  reference_price: number | string;
}

function MaterialForm({
  resource,
  units,
  onClose,
}: {
  resource: ResourceOut | null;
  units: UnitOfMeasureOut[];
  onClose: () => void;
}) {
  const createResource = useCreateResource();
  const updateResource = useUpdateResource();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const saving = createResource.isPending || updateResource.isPending;

  const form = useForm<FormValues>({
    initialValues: {
      name: resource?.name ?? "",
      type: (resource?.type as ResourceType | undefined) ?? null,
      unit_of_measure_id: resource
        ? (findUnitId(units, resource.unit.code)?.toString() ?? null)
        : null,
      reference_price: resource?.reference_price ?? "",
    },
    validate: {
      name: (value) => {
        const name = value.trim();
        if (name.length === 0) return "Ingresá el nombre del material";
        return name.length <= MAX_NAME
          ? null
          : `Como máximo ${MAX_NAME} caracteres`;
      },
      type: (value) => (value ? null : "Elegí un tipo"),
      unit_of_measure_id: (value) => (value ? null : "Elegí una unidad"),
      reference_price: (value) => {
        if (value === "") return "Ingresá el precio";
        return Number(value) >= 0 ? null : "El precio no puede ser negativo";
      },
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);

    // Never null here: validate() has already run.
    const payload: ResourceWrite = {
      name: values.name.trim(),
      type: values.type as ResourceType,
      unit_of_measure_id: Number(values.unit_of_measure_id),
      reference_price: String(Number(values.reference_price)),
    };

    try {
      const saved = resource
        ? await updateResource.mutateAsync({
            resourceId: resource.id,
            payload,
          })
        : await createResource.mutateAsync(payload);
      notifications.show({
        title: resource ? "Material actualizado" : "Material creado",
        message: resource
          ? `Guardamos los cambios de ${saved.name}.`
          : `${saved.name} ya forma parte del catálogo.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // Stays open with the message above the fields. The 409 to expect is
      // "ya existe un material activo con ese nombre", worded by the backend.
      setSubmitError(apiErrorMessage(error, "No pudimos guardar el material."));
    }
  });

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <TextInput
          label="Nombre"
          placeholder="Cemento portland (bolsa 50 kg)"
          {...form.getInputProps("name")}
        />

        <Select
          label="Tipo"
          data={TYPE_OPTIONS}
          {...form.getInputProps("type")}
        />

        <Select
          label="Unidad"
          placeholder="Elegí una unidad"
          data={units.map((unit) => ({
            value: unit.id.toString(),
            label: `${unit.name} (${unit.abbreviation})`,
          }))}
          {...form.getInputProps("unit_of_measure_id")}
        />

        <NumberInput
          label="Precio de referencia"
          placeholder="0"
          decimalScale={2}
          decimalSeparator=","
          thousandSeparator="."
          allowNegative={false}
          hideControls
          inputMode="decimal"
          {...form.getInputProps("reference_price")}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            {resource ? "Guardar" : "Crear material"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
