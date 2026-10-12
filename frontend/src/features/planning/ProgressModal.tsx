import { useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Slider,
  Stack,
  Text,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import type { TaskOut } from "./types";
import { useSetTaskProgress } from "./usePlanning";

interface ProgressModalProps {
  /** The task whose progress is being recorded, or null while closed. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Records how much of a task is done, from 0 to 100 (HU-16).
 *
 * Offered only for a task in progress or paused, which is why its menu does
 * not show this for the other two: the status rules the progress, so a
 * pending task is at 0% and a finished one at 100% (ADR-009 13).
 *
 * Reaching 100% does not finish the task. Finishing records a date and has
 * its own confirmation, so this says so instead of doing it on the side. */
export function ProgressModal({
  task,
  firmId,
  projectId,
  onClose,
}: ProgressModalProps) {
  return (
    <Modal
      opened={task !== null}
      onClose={onClose}
      title={task ? `Avance de ${task.name}` : ""}
      centered
    >
      {/* Keyed by task, so its initial value is always that task's. */}
      {task && (
        <ProgressForm
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

function ProgressForm({
  task,
  firmId,
  projectId,
  onClose,
}: ProgressModalProps & { task: TaskOut }) {
  const setProgress = useSetTaskProgress(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // An empty NumberInput gives "", hence the union.
  const form = useForm<{ progress_percent: number | string }>({
    initialValues: { progress_percent: task.progress_percent },
    validate: {
      progress_percent: (value) =>
        typeof value === "number" &&
        Number.isInteger(value) &&
        value >= 0 &&
        value <= 100
          ? null
          : "Ingresá un número entero entre 0 y 100",
    },
  });
  const value = form.values.progress_percent;

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      const updated = await setProgress.mutateAsync({
        taskId: task.id,
        progressPercent: Number(values.progress_percent),
      });
      notifications.show({
        title: "Avance registrado",
        message: `${task.name} quedó en ${updated.progress_percent}%.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos guardar el avance."));
    }
  });

  return (
    <form onSubmit={handleSubmit}>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        {/* Two controls over one value: the slider to drag on a phone, the
            number to type an exact one. */}
        <Slider
          min={0}
          max={100}
          step={5}
          label={(percent) => `${percent}%`}
          marks={[{ value: 0 }, { value: 50 }, { value: 100 }]}
          value={typeof value === "number" ? value : 0}
          onChange={(percent) =>
            form.setFieldValue("progress_percent", percent)
          }
          aria-label="Avance"
        />
        <NumberInput
          label="Avance real"
          suffix="%"
          min={0}
          max={100}
          allowDecimal={false}
          allowNegative={false}
          {...form.getInputProps("progress_percent")}
        />

        {value === 100 && (
          <Text size="sm" c="dimmed">
            Llegar al 100% no finaliza la tarea. Cuando termine, finalizala
            desde su estado para registrar la fecha real de fin.
          </Text>
        )}

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={onClose}
            disabled={setProgress.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={setProgress.isPending}>
            Guardar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
