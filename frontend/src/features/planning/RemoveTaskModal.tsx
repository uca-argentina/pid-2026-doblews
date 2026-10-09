import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { joinTaskNames } from "./taskFields";
import type { TaskOut } from "./types";
import { useRemoveTask } from "./usePlanning";

interface RemoveTaskModalProps {
  /** The task being removed, or null when the modal is closed. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Confirmation for taking a task out of the planning.
 *
 * It says what happens to the take-off, because that is the part a person
 * would worry about: the lines assigned to the task are not removed with it.
 * They go back to being unassigned, keep counting in the budget, and can be
 * given to another task (ADR-009 section 7). */
export function RemoveTaskModal({
  task,
  firmId,
  projectId,
  onClose,
}: RemoveTaskModalProps) {
  const removeTask = useRemoveTask(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleRemove = async () => {
    if (!task) return;

    setSubmitError(null);
    try {
      await removeTask.mutateAsync(task.id);
      notifications.show({
        title: "Tarea dada de baja",
        message: `${task.name} ya no está en la planificación.`,
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja la tarea."),
      );
    }
  };

  return (
    <Modal
      opened={task !== null}
      onClose={close}
      title={task ? `Dar de baja ${task.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          La tarea sale de la planificación. Sus líneas de cómputo no se dan de
          baja: vuelven a quedar sin asignar, siguen contando en el presupuesto
          y podés asignarlas a otra tarea.
        </Text>

        {/* Its dependencies go with it, both ways (ADR-009 section 7). Only
            the successors are named: they are the tasks whose dates and
            whose start this changes. */}
        {task && task.successors.length > 0 && (
          <Text size="sm">
            {task.successors.length === 1
              ? "Esta tarea deja de esperarla"
              : "Estas tareas dejan de esperarla"}{" "}
            y sus fechas se recalculan:{" "}
            {joinTaskNames(task.successors.map((successor) => successor.name))}.
          </Text>
        )}

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={removeTask.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleRemove}
            loading={removeTask.isPending}
          >
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
