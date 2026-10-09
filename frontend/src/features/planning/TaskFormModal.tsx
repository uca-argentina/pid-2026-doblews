import { useState } from "react";
import { useForm } from "@mantine/form";
import {
  Alert,
  Button,
  Group,
  Modal,
  MultiSelect,
  NumberInput,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { dependentsOf } from "./taskFields";
import type { TaskOut, TaskWrite } from "./types";
import {
  useCreateTask,
  usePlanning,
  useTaskAssignees,
  useUpdateTask,
} from "./usePlanning";

// The same limits the backend enforces, so the usual mistakes are caught
// before a round trip. They are not the protection: the API validates every
// field again, and this only spares the architect a 422 whose English field
// errors would not help them.
const MAX_NAME = 150;
const MAX_DURATION = 10_000;

interface TaskFormModalProps {
  opened: boolean;
  /** The task being edited, or null to create a new one. */
  task: TaskOut | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

interface FormValues {
  name: string;
  description: string;
  // NumberInput speaks number, or string while the value is empty.
  estimated_duration_days: number | string;
  not_before_date: string | null;
  assignee_account_id: string | null;
  // MultiSelect speaks strings too.
  predecessor_ids: string[];
}

/** HU-13's form, the same one for creating and for editing a task, with
 * HU-14's predecessors.
 *
 * One form because the backend has one shape for both: the edit is a PUT that
 * takes the whole task. The status and the actual dates are not here — they
 * change through the status actions, never through this form.
 *
 * The form lives in a child component so that it mounts fresh each time, as
 * in ProjectFormModal: its initial values are that task's current ones. */
export function TaskFormModal({
  opened,
  task,
  firmId,
  projectId,
  onClose,
}: TaskFormModalProps) {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={task ? `Editar ${task.name}` : "Nueva tarea"}
      centered
    >
      {opened && (
        <TaskForm
          key={task?.id ?? "new"}
          task={task}
          firmId={firmId}
          projectId={projectId}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function TaskForm({
  task,
  firmId,
  projectId,
  onClose,
}: Omit<TaskFormModalProps, "opened">) {
  const assignees = useTaskAssignees(firmId, projectId);
  // Already in the cache: the form is only opened from the planning screen.
  const planning = usePlanning(firmId, projectId);
  const createTask = useCreateTask(firmId, projectId);
  const updateTask = useUpdateTask(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const saving = createTask.isPending || updateTask.isPending;

  // Whoever may be assigned today, plus whoever this task already has. The
  // two can differ: someone whose role on the work was lowered, or who
  // finished the task and left the team, keeps it (ADR-009 section 6) and is
  // no longer among the eligible. Without adding them back, opening the form
  // would show the field empty and saving it would quietly unassign them.
  const options = (assignees.data ?? []).map((person) => ({
    value: person.account_id.toString(),
    label: person.name,
  }));
  if (
    task?.assignee &&
    !options.some(
      (option) => option.value === task.assignee?.account_id.toString(),
    )
  ) {
    options.push({
      value: task.assignee.account_id.toString(),
      label: task.assignee.name,
    });
  }

  // Every other live task, except the ones that already wait for this one:
  // picking any of those would close a cycle (HU-14).
  const tasks = planning.data?.tasks ?? [];
  const excluded = task ? dependentsOf(task.id, tasks) : new Set<number>();
  const predecessorOptions = tasks
    .filter((other) => other.id !== task?.id && !excluded.has(other.id))
    .map((other) => ({ value: other.id.toString(), label: other.name }));

  const form = useForm<FormValues>({
    initialValues: {
      name: task?.name ?? "",
      description: task?.description ?? "",
      estimated_duration_days: task?.estimated_duration_days ?? "",
      not_before_date: task?.not_before_date ?? null,
      // Mantine's Select speaks strings; the payload turns it back into a
      // number below.
      assignee_account_id: task?.assignee?.account_id.toString() ?? null,
      predecessor_ids:
        task?.predecessors.map((predecessor) => predecessor.id.toString()) ??
        [],
    },
    validate: {
      name: (value) => {
        const name = value.trim();
        if (name.length === 0) return "Ingresá el nombre de la tarea";
        return name.length <= MAX_NAME
          ? null
          : `Como máximo ${MAX_NAME} caracteres`;
      },
      estimated_duration_days: (value) => {
        if (value === "") return "Ingresá la duración";
        const days = Number(value);
        if (!Number.isInteger(days) || days <= 0) {
          return "La duración tiene que ser un número entero mayor que cero";
        }
        return days <= MAX_DURATION ? null : "La duración es demasiado larga";
      },
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);

    // Empty means empty, in every field: the form sends the whole task, so a
    // cleared assignee is an assignee removed and not one left alone.
    const payload: TaskWrite = {
      name: values.name.trim(),
      description: values.description.trim() || null,
      estimated_duration_days: Number(values.estimated_duration_days),
      not_before_date: values.not_before_date,
      assignee_account_id: values.assignee_account_id
        ? Number(values.assignee_account_id)
        : null,
      predecessor_ids: values.predecessor_ids.map(Number),
    };

    try {
      const saved = task
        ? await updateTask.mutateAsync({ taskId: task.id, payload })
        : await createTask.mutateAsync(payload);
      notifications.show({
        title: task ? "Tarea actualizada" : "Tarea creada",
        message: task
          ? `Guardamos los cambios de ${saved.name}.`
          : `${saved.name} ya está en la planificación.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // Stays open with the message above the fields. The 409s to expect are
      // a name another task of the work already has, an assignee who left
      // the team while the form was open, and a predecessor someone else
      // changed meanwhile so that it now closes a cycle; the wording is the
      // backend's.
      setSubmitError(apiErrorMessage(error, "No pudimos guardar la tarea."));
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
          placeholder="Mampostería planta baja"
          {...form.getInputProps("name")}
        />

        <NumberInput
          label="Duración estimada"
          description="En días hábiles, de lunes a viernes."
          placeholder="0"
          rightSection="días"
          rightSectionWidth={52}
          allowDecimal={false}
          allowNegative={false}
          hideControls
          inputMode="numeric"
          {...form.getInputProps("estimated_duration_days")}
        />

        <Select
          label="Responsable"
          description="Opcional. Alguien del equipo de la obra que pueda gestionar la planificación."
          placeholder={assignees.isLoading ? "Cargando…" : "Sin responsable"}
          clearable
          data={options}
          disabled={assignees.isLoading}
          error={assignees.isError ? "No pudimos cargar el equipo" : undefined}
          {...form.getInputProps("assignee_account_id")}
        />

        <MultiSelect
          label="Predecesoras"
          description="Opcional. Las tareas que tienen que estar finalizadas para que esta pueda empezar."
          placeholder={predecessorOptions.length ? "Ninguna" : undefined}
          data={predecessorOptions}
          searchable
          clearable
          nothingFoundMessage="No hay otra tarea con ese nombre"
          {...form.getInputProps("predecessor_ids")}
        />

        {/* Its value is already a "YYYY-MM-DD" string in Mantine 9, the same
            shape the API uses, as in ProjectFormModal. */}
        <DateInput
          label="No antes de"
          description="Opcional. La tarea no se planifica para empezar antes de este día."
          placeholder="DD/MM/AAAA"
          valueFormat="DD/MM/YYYY"
          clearable
          {...form.getInputProps("not_before_date")}
        />

        <Textarea
          label="Descripción"
          placeholder="Qué incluye la tarea, en pocas líneas."
          autosize
          minRows={2}
          maxRows={6}
          {...form.getInputProps("description")}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button type="submit" loading={saving}>
            {task ? "Guardar" : "Crear tarea"}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
