import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatQuantity } from "../../lib/format";
import type { TakeoffLineOut } from "./types";
import { useRemoveLine } from "./useTakeoff";

interface RemoveLineModalProps {
  /** The line to remove, or null while the modal is closed. */
  line: TakeoffLineOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Confirmation for taking a line out of the take-off.
 *
 * It says what changes on screen — the totals drop at once — because that is
 * what the architect will notice. It is a logical removal on the backend, but
 * no screen restores a line, so it does not promise that either. */
export function RemoveLineModal({
  line,
  firmId,
  projectId,
  onClose,
}: RemoveLineModalProps) {
  const removeLine = useRemoveLine(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleRemove = async () => {
    if (!line) return;
    setSubmitError(null);
    try {
      await removeLine.mutateAsync(line.id);
      notifications.show({
        title: "Línea dada de baja",
        message: `${line.recipe.name} ya no suma al cómputo.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja la línea."),
      );
    }
  };

  return (
    <Modal
      opened={line !== null}
      onClose={close}
      title="Dar de baja la línea"
      centered
    >
      {line && (
        <Stack gap="md">
          {submitError && (
            <Alert color="red" variant="light" role="alert">
              {submitError}
            </Alert>
          )}

          <Text size="sm">
            {formatQuantity(line.quantity)} {line.recipe.unit.abbreviation} de{" "}
            <Text span fw={600}>
              {line.recipe.name}
            </Text>
            {line.note ? ` (${line.note})` : ""} sale del cómputo, y sus
            materiales dejan de sumar en el total.
          </Text>

          <Group justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              onClick={close}
              disabled={removeLine.isPending}
            >
              Cancelar
            </Button>
            <Button
              color="red"
              onClick={handleRemove}
              loading={removeLine.isPending}
            >
              Dar de baja
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  );
}
