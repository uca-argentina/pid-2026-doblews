import { useState } from "react";
import {
  Alert,
  Button,
  Center,
  Checkbox,
  Group,
  Loader,
  Modal,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatQuantity } from "../../lib/format";
import type { TakeoffLineOut } from "../takeoff/types";
import { useTakeoff } from "../takeoff/useTakeoff";
import type { TaskOut } from "./types";
import { useSetTaskLines } from "./usePlanning";

interface TaskLinesModalProps {
  /** The task whose lines are being chosen, or null while closed. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** Chooses which lines of the work's take-off a task is made of. Their cost
 * is what the task costs (HU-13): nobody types an amount.
 *
 * It shows every line of the take-off and not only the free ones. A line that
 * is already in another task can be ticked, and that moves it here — a line is
 * in one task or in none — so each of those says where it is now, before it
 * is picked. */
export function TaskLinesModal({
  task,
  firmId,
  projectId,
  onClose,
}: TaskLinesModalProps) {
  const takeoff = useTakeoff(firmId, projectId);

  return (
    <Modal
      opened={task !== null}
      onClose={onClose}
      title={task ? `Líneas de cómputo de ${task.name}` : ""}
      centered
    >
      {task && takeoff.isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {task && takeoff.isError && (
        <Alert color="red" variant="light">
          No pudimos cargar el cómputo. Probá de nuevo en un momento.
        </Alert>
      )}

      {/* Mounted only once the lines are there, and keyed by task, so its
          initial selection is that task's current lines. */}
      {task && takeoff.data && (
        <TaskLinesForm
          key={task.id}
          task={task}
          lines={takeoff.data.lines}
          firmId={firmId}
          projectId={projectId}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function TaskLinesForm({
  task,
  lines,
  firmId,
  projectId,
  onClose,
}: {
  task: TaskOut;
  lines: TakeoffLineOut[];
  firmId: number;
  projectId: number;
  onClose: () => void;
}) {
  const setTaskLines = useSetTaskLines(firmId, projectId);
  const [selected, setSelected] = useState<string[]>(() =>
    lines
      .filter((line) => line.task?.id === task.id)
      .map((line) => line.id.toString()),
  );
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSave = async () => {
    setSubmitError(null);
    try {
      await setTaskLines.mutateAsync({
        taskId: task.id,
        lineIds: selected.map(Number),
      });
      notifications.show({
        title: "Líneas asignadas",
        message: `Actualizamos el cómputo de ${task.name}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect: one of the lines was removed from the take-off
      // while this was open.
      setSubmitError(apiErrorMessage(error, "No pudimos asignar las líneas."));
    }
  };

  if (lines.length === 0) {
    return (
      <Stack gap="md">
        <Text size="sm">
          El cómputo de esta obra todavía no tiene líneas. Cargá recetas en la
          pestaña Cómputo y después asignalas a la tarea.
        </Text>
        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>
            Cerrar
          </Button>
        </Group>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      {submitError && (
        <Alert color="red" variant="light" role="alert">
          {submitError}
        </Alert>
      )}

      <Text size="sm" c="dimmed">
        El costo de la tarea es la suma de las líneas que elijas, a precios de
        hoy.
      </Text>

      <Checkbox.Group value={selected} onChange={setSelected}>
        <Stack gap="sm">
          {lines.map((line) => (
            <Checkbox
              key={line.id}
              value={line.id.toString()}
              label={
                <>
                  {line.recipe.name} · {formatQuantity(line.quantity)}{" "}
                  {line.recipe.unit.abbreviation}
                  {line.note && ` · ${line.note}`}
                </>
              }
              description={
                line.task && line.task.id !== task.id
                  ? `Hoy está en "${line.task.name}". Si la elegís, pasa a esta tarea.`
                  : undefined
              }
            />
          ))}
        </Stack>
      </Checkbox.Group>

      <Group justify="flex-end" gap="sm">
        <Button
          variant="subtle"
          onClick={onClose}
          disabled={setTaskLines.isPending}
        >
          Cancelar
        </Button>
        <Button onClick={handleSave} loading={setTaskLines.isPending}>
          Guardar
        </Button>
      </Group>
    </Stack>
  );
}
