import { useState } from "react";
import { Alert, Badge, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { LineFields } from "./LineFields";
import { linePayload, lineValidation, type LineValues } from "./lineForm";
import type { TakeoffLineOut } from "./types";
import { useUpdateLine } from "./useTakeoff";

interface EditLineModalProps {
  /** The line being edited, or null while the modal is closed. */
  line: TakeoffLineOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Change how much of a recipe a line takes, or its note.
 *
 * The recipe is shown and not offered: changing it would change the unit the
 * quantity is in, so 120 m2 of wall would silently become 120 of something
 * else. The text under it says the honest way to do that instead. */
export function EditLineModal({
  line,
  firmId,
  projectId,
  onClose,
}: EditLineModalProps) {
  return (
    <Modal
      opened={line !== null}
      onClose={onClose}
      title="Editar línea del cómputo"
      centered
    >
      {/* Keyed by line, so its initial values are always that line's. */}
      {line && (
        <EditLineForm
          key={line.id}
          line={line}
          firmId={firmId}
          projectId={projectId}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function EditLineForm({
  line,
  firmId,
  projectId,
  onClose,
}: EditLineModalProps & { line: TakeoffLineOut }) {
  const updateLine = useUpdateLine(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<LineValues>({
    initialValues: { quantity: Number(line.quantity), note: line.note ?? "" },
    validate: lineValidation,
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      await updateLine.mutateAsync({
        lineId: line.id,
        payload: linePayload(values),
      });
      notifications.show({
        title: "Línea actualizada",
        message: `Guardamos los cambios de ${line.recipe.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos guardar la línea."));
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

        <div>
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Text fw={600}>{line.recipe.name}</Text>
            <Badge variant="light" style={{ flexShrink: 0 }}>
              por {line.recipe.unit.abbreviation}
            </Badge>
          </Group>
          <Text size="xs" c="dimmed">
            Para usar otra receta, dá de baja esta línea y agregá la nueva.
          </Text>
        </div>

        <LineFields form={form} unit={line.recipe.unit.abbreviation} />

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={onClose}
            disabled={updateLine.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={updateLine.isPending}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
