import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  useMantineTheme,
} from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import type { RecipeOut, RecipeWrite, ResourceOut } from "../catalog/types";
import type { UnitOfMeasureOut } from "../units-of-measure/types";
import { findUnitId } from "../units-of-measure/unitLookup";
import { useUnitsOfMeasure } from "../units-of-measure/useUnitsOfMeasure";
import type { RecipeWriter } from "./types";

// Same limit as recipe.name (String(150)).
const MAX_NAME = 150;

interface RecipeFormModalProps {
  opened: boolean;
  /** The recipe being edited, or null to create a new one. */
  recipe: RecipeOut | null;
  onClose: () => void;
  /** The resources a line may use, or undefined while they load. Always the
   * system's (ADR-006 rule 3), but each screen reads them from its own
   * endpoint: support from /platform, a firm from its catalogue. */
  resources: ResourceOut[] | undefined;
  /** Where saving goes: support's endpoint or the firm's. */
  writer: RecipeWriter;
}

/** The create/edit form for one recipe, for support's general recipes (HU-8)
 * and a firm's own (HU-9) alike: header and every one of its lines, replaced
 * whole — the master-detail screen ADR-005 section 3
 * flags as the hardest one, and the first form in this app editing an
 * array of rows in a single submit.
 *
 * A modal (size="lg", fullScreen on phone like AddLineModal) rather than a
 * dedicated page, and deliberately built to be usable at 375px: each line
 * renders as a compact row from "sm" up and as a stacked card below it,
 * the same table/card duality every list screen in this app already uses,
 * just applied to a form's rows instead of a table's.
 *
 * The inner form waits for both the units of measure and the resources
 * list to load before mounting, for the same reason as MaterialFormModal:
 * RecipeOut.unit only carries {code, abbreviation}, and a line only
 * carries resource_id, so editing has to resolve both against catalogues
 * loaded elsewhere before useForm's initialValues can be computed once. */
export function RecipeFormModal({
  opened,
  recipe,
  onClose,
  resources,
  writer,
}: RecipeFormModalProps) {
  const theme = useMantineTheme();
  const isPhone = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);
  const units = useUnitsOfMeasure();

  const loading = units.isLoading || resources === undefined;

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={recipe ? `Editar ${recipe.name}` : "Nueva receta"}
      fullScreen={isPhone}
      size="lg"
      centered
    >
      {opened &&
        (loading ? (
          <Center py="md">
            <Loader />
          </Center>
        ) : (
          <RecipeForm
            key={recipe?.id ?? "new"}
            recipe={recipe}
            units={units.data ?? []}
            resources={resources ?? []}
            writer={writer}
            onClose={onClose}
          />
        ))}
    </Modal>
  );
}

interface LineFormValues {
  // Select speaks strings; the payload turns it back into a number below.
  resource_id: string | null;
  quantity_per_unit: number | string;
}

interface FormValues {
  name: string;
  description: string;
  unit_of_measure_id: string | null;
  lines: LineFormValues[];
}

function RecipeForm({
  recipe,
  units,
  resources,
  writer,
  onClose,
}: {
  recipe: RecipeOut | null;
  units: UnitOfMeasureOut[];
  resources: ResourceOut[];
  writer: RecipeWriter;
  onClose: () => void;
}) {
  const [submitError, setSubmitError] = useState<string | null>(null);

  const saving = writer.saving;

  const form = useForm<FormValues>({
    initialValues: {
      name: recipe?.name ?? "",
      description: recipe?.description ?? "",
      unit_of_measure_id: recipe
        ? (findUnitId(units, recipe.unit.code)?.toString() ?? null)
        : null,
      lines: recipe
        ? recipe.lines.map((line) => ({
            resource_id: line.resource_id.toString(),
            quantity_per_unit: Number(line.quantity_per_unit),
          }))
        : [],
    },
    validate: {
      name: (value) => {
        const name = value.trim();
        if (name.length === 0) return "Ingresá el nombre de la receta";
        return name.length <= MAX_NAME
          ? null
          : `Como máximo ${MAX_NAME} caracteres`;
      },
      unit_of_measure_id: (value) => (value ? null : "Elegí una unidad"),
      lines: {
        // A material repeated across two lines is refused by the backend
        // (422); catching it here marks every line that collides, not
        // only the second one, so the picker itself shows the conflict.
        resource_id: (value, values) => {
          if (!value) return "Elegí un material";
          const repeated = values.lines.filter(
            (line) => line.resource_id === value,
          ).length;
          return repeated > 1 ? "Este material ya está en otra línea" : null;
        },
        quantity_per_unit: (value) => {
          if (value === "") return "Ingresá la cantidad";
          return Number(value) > 0
            ? null
            : "La cantidad tiene que ser mayor que cero";
        },
      },
    },
  });

  const resourceOptions = resources.map((resource) => ({
    value: resource.id.toString(),
    label: `${resource.name} (${resource.unit.abbreviation})`,
  }));

  const isLaborOrEquipment = (resource: ResourceOut) =>
    resource.type === "labor" || resource.type === "equipment";

  const unitAbbreviationFor = (resourceId: string | null) =>
    resources.find((resource) => resource.id.toString() === resourceId)?.unit
      .abbreviation ?? "";

  const quantityLabel = (selectedResourceId: string | null) => {
    const resource = resources.find((r) => r.id.toString() === selectedResourceId);
    return resource && isLaborOrEquipment(resource) ? "Horas" : "Cantidad";
  };

  const addLine = () =>
    form.insertListItem("lines", { resource_id: null, quantity_per_unit: "" });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);

    // Never null here: validate() has already run.
    const payload: RecipeWrite = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      unit_of_measure_id: Number(values.unit_of_measure_id),
      lines: values.lines.map((line) => ({
        resource_id: Number(line.resource_id),
        // String(Number(...)) and not the raw value: the input is limited
        // to four decimals, so this prints exactly what was typed, with a
        // dot whatever the separator on screen (same as HU-5's linePayload).
        quantity_per_unit: String(Number(line.quantity_per_unit)),
      })),
    };

    try {
      const saved = await writer.save(payload, recipe?.id ?? null);
      notifications.show({
        title: recipe ? "Receta actualizada" : "Receta creada",
        message: recipe
          ? `Guardamos los cambios de ${saved.name}.`
          : `${saved.name} ya forma parte del catálogo.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect is a duplicate name; a 422 that slipped past the
      // checks above (a material deactivated in another tab, say) shows
      // the backend's own text too, since apiErrorMessage passes both
      // through when their detail is a plain string.
      setSubmitError(apiErrorMessage(error, "No pudimos guardar la receta."));
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
          placeholder="Revoque grueso"
          {...form.getInputProps("name")}
        />

        <Textarea
          label="Descripción"
          placeholder="La proporción de la mezcla, el espesor supuesto…"
          autosize
          minRows={2}
          maxRows={6}
          {...form.getInputProps("description")}
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

        <div>
          <Group justify="space-between" align="center" mb="xs">
            <Text fw={500} size="sm">
              Líneas
            </Text>
            <Button variant="light" size="compact-sm" onClick={addLine}>
              Agregar línea
            </Button>
          </Group>

          {form.values.lines.length === 0 && (
            <Text c="red" size="sm" mb="xs">
              La receta necesita al menos una línea.
            </Text>
          )}

          {/* A compact row from "sm" up... */}
          <Box visibleFrom="sm">
            <Stack gap="xs">
              {form.values.lines.map((line, index) => (
                <Group key={index} align="flex-start" wrap="nowrap">
                  <Select
                    placeholder="Elegí un material"
                    searchable
                    data={resourceOptions}
                    style={{ flex: 1 }}
                    {...form.getInputProps(`lines.${index}.resource_id`)}
                  />
                  <NumberInput
                    label={quantityLabel(line.resource_id)}
                    placeholder="0.0"
                    w={160}
                    rightSection={unitAbbreviationFor(line.resource_id)}
                    decimalScale={4}
                    decimalSeparator=","
                    thousandSeparator="."
                    allowNegative={false}
                    hideControls
                    inputMode="decimal"
                    {...form.getInputProps(`lines.${index}.quantity_per_unit`)}
                  />
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    mt={4}
                    aria-label="Quitar línea"
                    onClick={() => form.removeListItem("lines", index)}
                  >
                    ✕
                  </ActionIcon>
                </Group>
              ))}
            </Stack>
          </Box>

          {/* ...a stacked card below it, same duality every list in this
              app already uses for its rows. */}
          <Stack gap="xs" hiddenFrom="sm">
            {form.values.lines.map((line, index) => (
              <Card key={index} withBorder padding="sm" radius="md">
                <Stack gap="xs">
                  <Select
                    label="Material"
                    placeholder="Elegí un material"
                    searchable
                    data={resourceOptions}
                    {...form.getInputProps(`lines.${index}.resource_id`)}
                  />
                  <NumberInput
                    label={quantityLabel(line.resource_id)}
                    placeholder="0"
                    rightSection={unitAbbreviationFor(line.resource_id)}
                    decimalScale={4}
                    decimalSeparator=","
                    thousandSeparator="."
                    allowNegative={false}
                    hideControls
                    inputMode="decimal"
                    {...form.getInputProps(`lines.${index}.quantity_per_unit`)}
                  />
                  <Button
                    variant="subtle"
                    color="red"
                    size="compact-sm"
                    onClick={() => form.removeListItem("lines", index)}
                  >
                    Quitar línea
                  </Button>
                </Stack>
              </Card>
            ))}
          </Stack>
        </div>

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button
            type="submit"
            loading={saving}
            disabled={form.values.lines.length === 0}
          >
            {recipe ? "Guardar" : "Crear receta"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
