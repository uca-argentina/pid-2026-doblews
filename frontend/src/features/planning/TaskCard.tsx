import type { ReactNode } from "react";
import { Card, Group, Stack, Text, UnstyledButton } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { SlackBadge } from "./SlackBadge";
import { formatWorkingDays, taskEnd, taskStart } from "./taskFields";
import { TaskDateText } from "./TaskDateText";
import { TaskProgress } from "./TaskProgress";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface TaskCardProps {
  task: TaskOut;
  currency: string;
  /** Whether the work has a planning fixed (HU-16). */
  baselineFixed: boolean;
  /** Opens the task's detail, from its name. */
  onOpen: (task: TaskOut) => void;
  /** The status as a control that changes it, for those who may manage the
   * planning. Omitted for everyone else, who get the plain badge. */
  status?: ReactNode;
  /** What this task offers to do, for those who may manage the planning. */
  actions?: ReactNode;
}

/** One task on a phone. Same data as a table row, stacked instead of side by
 * side, so 375px needs no horizontal scrolling.
 *
 * The dates take one line, start to end, and only once there is something to
 * show: with no start date on the work nothing is planned, and two dashes
 * would be noise on a small screen. A critical task gets a red border, as the
 * row of the table gets its badge (HU-14). */
export function TaskCard({
  task,
  currency,
  baselineFixed,
  onOpen,
  status,
  actions,
}: TaskCardProps) {
  return (
    <Card
      withBorder
      padding="md"
      radius="md"
      style={
        task.is_critical
          ? { borderColor: "var(--mantine-color-red-filled)" }
          : undefined
      }
    >
      <Stack gap={6}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <UnstyledButton
            className="name-link"
            onClick={() => onOpen(task)}
            aria-label={`Ver el detalle de ${task.name}`}
          >
            <Text fw={600} c="inherit">
              {task.name}
            </Text>
          </UnstyledButton>
          {status ?? <TaskStatusBadge status={task.status} />}
        </Group>

        {task.description && (
          <Text size="sm" c="dimmed" lineClamp={3}>
            {task.description}
          </Text>
        )}

        <Text size="sm">
          {task.assignee?.name ?? "Sin responsable"} ·{" "}
          {formatWorkingDays(task.estimated_duration_days)}
        </Text>

        {task.planned_start_date !== null && (
          <Group justify="space-between" wrap="nowrap" gap="xs">
            <Text size="sm">
              <TaskDateText date={taskStart(task)} /> →{" "}
              <TaskDateText date={taskEnd(task)} />
            </Text>
            <SlackBadge task={task} labelled />
          </Group>
        )}

        <TaskProgress task={task} baselineFixed={baselineFixed} />

        {(task.cost !== null || actions) && (
          <Group justify="space-between" wrap="nowrap" align="center" mt={4}>
            <Text size="sm" fw={500}>
              {task.cost !== null && formatMoney(task.cost, currency)}
            </Text>
            {actions}
          </Group>
        )}
      </Stack>
    </Card>
  );
}
