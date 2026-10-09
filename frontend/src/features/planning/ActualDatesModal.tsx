import { useState } from "react";
import { Alert, Button, Group, Modal, Stack } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { apiErrorMessage } from "../../lib/apiError";
import type { TaskOut } from "./types";
import { useUpdateTaskActualDates } from "./usePlanning";

interface ActualDatesModalProps {
  /** The task whose dates are being corrected, or null while closed. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Corrects the dates that starting and finishing a task recorded, without
 * changing its status (HU-13: "por defecto hoy, y se pueden corregir").
 *
 * Only the dates the task's status carries are shown: the start once it began,
 * and the end only when it is finished. A pending task has neither, which is
 * why its menu does not offer this at all. To remove a date rather than move
 * it, the status actions are the way: "deshacer inicio" and "reabrir". */
export function ActualDatesModal({
  task,
  firmId,
  projectId,
  onClose,
}: ActualDatesModalProps) {
  return (
    <Modal
      opened={task !== null}
      onClose={onClose}
      title={task ? `Corregir fechas de ${task.name}` : ""}
      centered
    >
      {/* Keyed by task, so its initial values are always that task's. */}
      {task && (
        <ActualDatesForm
          key={task.id}
          task={task}
          firmId={firmId}
          projectId={projectId}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function ActualDatesForm({
  task,
  firmId,
  projectId,
  onClose,
}: ActualDatesModalProps & { task: TaskOut }) {
  const updateDates = useUpdateTaskActualDates(firmId, projectId);
  const finished = task.status === "finished";
  const today = dayjs().format("YYYY-MM-DD");
  const [start, setStart] = useState<string | null>(task.actual_start_date);
  const [end, setEnd] = useState<string | null>(task.actual_end_date);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const incomplete = !start || (finished && !end);

  const handleSave = async () => {
    if (incomplete) return;

    setSubmitError(null);
    try {
      await updateDates.mutateAsync({
        taskId: task.id,
        // Both keys every time. The end is only sent for a finished task;
        // for any other the backend expects it empty.
        payload: {
          actual_start_date: start,
          actual_end_date: finished ? end : null,
        },
      });
      notifications.show({
        title: "Fechas corregidas",
        message: `Guardamos las fechas reales de ${task.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos guardar las fechas."));
    }
  };

  return (
    <Stack gap="md">
      {submitError && (
        <Alert color="red" variant="light" role="alert">
          {submitError}
        </Alert>
      )}

      <DateInput
        label="Fecha real de inicio"
        valueFormat="DD/MM/YYYY"
        value={start}
        onChange={setStart}
        // Not after the end, when there is one, and never after today.
        maxDate={finished && end ? end : today}
        error={start ? undefined : "Elegí una fecha"}
      />

      {finished && (
        <DateInput
          label="Fecha real de fin"
          valueFormat="DD/MM/YYYY"
          value={end}
          onChange={setEnd}
          minDate={start ?? undefined}
          maxDate={today}
          error={end ? undefined : "Elegí una fecha"}
        />
      )}

      <Group justify="flex-end" gap="sm">
        <Button
          variant="subtle"
          onClick={onClose}
          disabled={updateDates.isPending}
        >
          Cancelar
        </Button>
        <Button
          onClick={handleSave}
          loading={updateDates.isPending}
          disabled={incomplete}
        >
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}
