import type { ReactNode } from "react";
import {
  Badge,
  Group,
  Modal,
  SimpleGrid,
  Stack,
  Text,
  UnstyledButton,
} from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { EMPTY, formatDate } from "../projects/projectFields";
import { formatWorkingDays } from "./taskFields";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut, TaskRefOut } from "./types";

interface TaskDetailModalProps {
  /** The task being looked at, or null when the modal is closed. */
  task: TaskOut | null;
  currency: string;
  /** Opens another task's detail in place of this one: a predecessor or a
   * successor, so the chain can be walked without closing anything. */
  onSelect: (taskId: number) => void;
  onClose: () => void;
}

/** "La tarea" of HU-14: everything about one task, read only.
 *
 * Open to whoever sees the planning, the client included, because it is
 * where a task's predecessors and successors are listed with their status —
 * which the listing has no room for. Editing stays in the ⋯ menu's form. The
 * cost is shown only when the response carries it.
 *
 * HU-15's "elegir una tarea en la vista abre su detalle" is meant to open
 * this same modal. */
export function TaskDetailModal({
  task,
  currency,
  onSelect,
  onClose,
}: TaskDetailModalProps) {
  return (
    <Modal
      opened={task !== null}
      onClose={onClose}
      title={task?.name ?? ""}
      centered
      size="lg"
    >
      {task && (
        <TaskDetail task={task} currency={currency} onSelect={onSelect} />
      )}
    </Modal>
  );
}

function TaskDetail({
  task,
  currency,
  onSelect,
}: {
  task: TaskOut;
  currency: string;
  onSelect: (taskId: number) => void;
}) {
  return (
    <Stack gap="md">
      <Group gap="xs">
        <TaskStatusBadge status={task.status} />
        {task.is_critical && (
          <Badge color="red" variant="light">
            Crítica
          </Badge>
        )}
      </Group>

      {task.description && <Text size="sm">{task.description}</Text>}

      <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="sm" verticalSpacing="sm">
        <Field label="Responsable">
          {task.assignee?.name ?? "Sin responsable"}
        </Field>
        <Field label="Duración estimada">
          {formatWorkingDays(task.estimated_duration_days)}
        </Field>
        <Field label="Inicio previsto">
          {formatDate(task.planned_start_date)}
        </Field>
        <Field label="Fin previsto">{formatDate(task.planned_end_date)}</Field>
        <Field label="Inicio real">{formatDate(task.actual_start_date)}</Field>
        <Field label="Fin real">{formatDate(task.actual_end_date)}</Field>
        <Field label="Holgura">
          {task.slack_days === null
            ? EMPTY
            : task.is_critical
              ? "Crítica: cualquier atraso corre el fin de la obra"
              : formatWorkingDays(task.slack_days)}
        </Field>
        {task.not_before_date && (
          <Field label="No antes de">{formatDate(task.not_before_date)}</Field>
        )}
        {task.cost !== null && (
          <Field label="Costo">{formatMoney(task.cost, currency)}</Field>
        )}
      </SimpleGrid>

      <Dependencies
        title="Predecesoras"
        hint="Tienen que estar finalizadas para que esta pueda empezar."
        empty="Ninguna: puede empezar con la obra."
        tasks={task.predecessors}
        onSelect={onSelect}
      />
      <Dependencies
        title="Sucesoras"
        hint="Esperan a que esta finalice para empezar."
        empty="Ninguna tarea espera a esta."
        tasks={task.successors}
        onSelect={onSelect}
      />
    </Stack>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="sm">{children}</Text>
    </div>
  );
}

/** One side of a task's dependencies, each with its status, each opening its
 * own detail. */
function Dependencies({
  title,
  hint,
  empty,
  tasks,
  onSelect,
}: {
  title: string;
  hint: string;
  empty: string;
  tasks: TaskRefOut[];
  onSelect: (taskId: number) => void;
}) {
  return (
    <Stack gap={6}>
      <div>
        <Text size="sm" fw={600}>
          {title}
        </Text>
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      </div>
      {tasks.length === 0 ? (
        <Text size="sm" c="dimmed">
          {empty}
        </Text>
      ) : (
        tasks.map((other) => (
          <Group key={other.id} justify="space-between" wrap="nowrap" gap="sm">
            <UnstyledButton
              onClick={() => onSelect(other.id)}
              aria-label={`Ver ${other.name}`}
            >
              <Text size="sm" c="obra" td="underline">
                {other.name}
              </Text>
            </UnstyledButton>
            <TaskStatusBadge status={other.status} />
          </Group>
        ))
      )}
    </Stack>
  );
}
