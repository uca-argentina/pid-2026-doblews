import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatDate } from "../projects/projectFields";
import { useFixBaseline } from "./usePlanning";

interface FixBaselineModalProps {
  opened: boolean;
  /** The day the planning was last fixed, or null if it never was. */
  fixedOn: string | null;
  /** When the work is planned to end today: what fixing would keep. */
  plannedEndDate: string | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Confirmation for fixing the planning (HU-16).
 *
 * It says what is kept — today's planned dates — and, when there already is
 * one, that this replaces it: there is no history of them (ADR-009 13), so
 * the comparison made so far is gone once this is confirmed. */
export function FixBaselineModal({
  opened,
  fixedOn,
  plannedEndDate,
  firmId,
  projectId,
  onClose,
}: FixBaselineModalProps) {
  const fix = useFixBaseline(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleFix = async () => {
    setSubmitError(null);
    try {
      await fix.mutateAsync();
      notifications.show({
        title: "Planificación fijada",
        message: "El avance se compara desde ahora contra las fechas de hoy.",
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos fijar la planificación."),
      );
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title={
        fixedOn ? "Volver a fijar la planificación" : "Fijar planificación"
      }
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Se guardan las fechas previstas de hoy de cada tarea
          {plannedEndDate
            ? `, y el fin de la obra el ${formatDate(plannedEndDate)}, `
            : " "}
          como lo planificado. El avance de cada tarea se compara contra esa
          copia, que no se mueve cuando las fechas previstas se corren.
        </Text>

        {fixedOn && (
          <Text size="sm">
            Reemplaza la planificación fijada el {formatDate(fixedOn)}: la
            anterior no se conserva. Las tareas creadas desde entonces entran en
            la comparación.
          </Text>
        )}

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={close} disabled={fix.isPending}>
            Cancelar
          </Button>
          <Button onClick={handleFix} loading={fix.isPending}>
            {fixedOn ? "Volver a fijar" : "Fijar planificación"}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
