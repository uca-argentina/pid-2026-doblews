import { useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { usePlanning } from "../planning/usePlanning";
import type { TakeoffLineOut } from "./types";
import { useSetLineTask } from "./useTakeoff";

interface AssignLineTaskModalProps {
  /** The line being assigned, or null while the modal is closed. */
  line: TakeoffLineOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Puts one line of the take-off in a task of the work's planning, or takes
 * it out of the one it is in (HU-13: "se puede cambiar desde ahí").
 *
 * The take-off's side of the same link the planning writes from the task's
 * side. Leaving the field empty is "sin asignar": the line keeps counting in
 * the budget and shows up in the planning as not assigned to any task. */
export function AssignLineTaskModal({
  line,
  firmId,
  projectId,
  onClose,
}: AssignLineTaskModalProps) {
  return (
    <Modal
      opened={line !== null}
      onClose={onClose}
      title="Asignar a una tarea"
      centered
    >
      {/* Keyed by line, so its initial value is always that line's task. */}
      {line && (
        <AssignLineTaskForm
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

function AssignLineTaskForm({
  line,
  firmId,
  projectId,
  onClose,
}: AssignLineTaskModalProps & { line: TakeoffLineOut }) {
  const planning = usePlanning(firmId, projectId);
  const setLineTask = useSetLineTask(firmId, projectId);
  const [taskId, setTaskId] = useState<string | null>(
    line.task?.id.toString() ?? null,
  );
  const [submitError, setSubmitError] = useState<string | null>(null);

  const tasks = planning.data?.tasks ?? [];
  const noTasksYet =
    !planning.isLoading && !planning.isError && tasks.length === 0;

  const handleSave = async () => {
    setSubmitError(null);
    try {
      const saved = await setLineTask.mutateAsync({
        lineId: line.id,
        taskId: taskId ? Number(taskId) : null,
      });
      notifications.show({
        title: saved.task ? "Línea asignada" : "Línea sin asignar",
        message: saved.task
          ? `${line.recipe.name} quedó en ${saved.task.name}.`
          : `${line.recipe.name} ya no está en ninguna tarea.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect: that task was removed from the planning while the
      // picker was open.
      setSubmitError(apiErrorMessage(error, "No pudimos asignar la línea."));
    }
  };

  return (
    <Stack gap="md">
      {submitError && (
        <Alert color="red" variant="light" role="alert">
          {submitError}
        </Alert>
      )}

      <div>
        <Text fw={600}>{line.recipe.name}</Text>
        {line.note && (
          <Text size="sm" c="dimmed">
            {line.note}
          </Text>
        )}
      </div>

      <Select
        label="Tarea"
        description={
          noTasksYet
            ? "Las tareas se cargan en la pestaña Planificación."
            : "Dejalo vacío para que la línea quede sin asignar."
        }
        placeholder={
          planning.isLoading
            ? "Cargando…"
            : noTasksYet
              ? "Esta obra todavía no tiene tareas"
              : "Sin asignar"
        }
        clearable
        data={tasks.map((task) => ({
          value: task.id.toString(),
          label: task.name,
        }))}
        disabled={planning.isLoading || planning.isError || noTasksYet}
        error={
          planning.isError ? "No pudimos cargar la planificación" : undefined
        }
        value={taskId}
        onChange={setTaskId}
      />

      <Group justify="flex-end" gap="sm">
        <Button
          variant="subtle"
          onClick={onClose}
          disabled={setLineTask.isPending}
        >
          Cancelar
        </Button>
        <Button
          onClick={handleSave}
          loading={setLineTask.isPending}
          disabled={planning.isLoading || planning.isError}
        >
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}
