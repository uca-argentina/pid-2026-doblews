import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { joinTaskNames, startedSuccessors } from "./taskFields";
import type { TaskOut } from "./types";
import { useTransitionTask } from "./usePlanning";

interface ReopenTaskModalProps {
  /** The task being reopened, or null when the modal is closed. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Confirmation for reopening a task whose successors already started.
 *
 * Allowed, on purpose (ADR-009 section 5): rework happens, and what was
 * already done is not undone. The successors keep their actual dates; the
 * modal only makes sure that is a decision and not a slip. A task with no
 * started successors is reopened in one click and never gets here. */
export function ReopenTaskModal({
  task,
  firmId,
  projectId,
  onClose,
}: ReopenTaskModalProps) {
  const transitionTask = useTransitionTask(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleReopen = async () => {
    if (!task) return;

    setSubmitError(null);
    try {
      await transitionTask.mutateAsync({
        taskId: task.id,
        payload: { action: "reopen" },
      });
      notifications.show({
        title: `Reabrir: ${task.name}`,
        message: "La tarea quedó en curso.",
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos reabrir la tarea."));
    }
  };

  const started = task ? startedSuccessors(task) : [];

  return (
    <Modal
      opened={task !== null}
      onClose={close}
      title={task ? `Reabrir ${task.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          {started.length === 1
            ? "Esta tarea espera a la que vas a reabrir y ya empezó: "
            : "Estas tareas esperan a la que vas a reabrir y ya empezaron: "}
          {joinTaskNames(started)}.
        </Text>
        <Text size="sm">
          {started.length === 1
            ? "Sigue como está, con sus fechas reales. "
            : "Siguen como están, con sus fechas reales. "}
          La tarea vuelve a quedar en curso y su fin se calcula de nuevo.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={transitionTask.isPending}
          >
            Cancelar
          </Button>
          <Button onClick={handleReopen} loading={transitionTask.isPending}>
            Reabrir
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
