import type { ReactNode } from "react";
import { Card, Group, Stack, Text } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { formatDate } from "../projects/projectFields";
import { formatDuration } from "./taskFields";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface TaskCardProps {
  task: TaskOut;
  currency: string;
  /** What this task offers to do, for those who may manage the planning. */
  actions?: ReactNode;
}

/** One task on a phone. Same data as a table row, stacked instead of side by
 * side, so 375px needs no horizontal scrolling.
 *
 * The actual dates only take a line once there is one to show: a pending task
 * has neither, and two dashes would be noise on a small screen. */
export function TaskCard({ task, currency, actions }: TaskCardProps) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={6}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600}>{task.name}</Text>
          <TaskStatusBadge status={task.status} />
        </Group>

        {task.description && (
          <Text size="sm" c="dimmed" lineClamp={3}>
            {task.description}
          </Text>
        )}

        <Text size="sm">
          {task.assignee?.name ?? "Sin responsable"} ·{" "}
          {formatDuration(task.estimated_duration_days)} hábiles
        </Text>

        {task.actual_start_date && (
          <Text size="xs" c="dimmed">
            Inicio real: {formatDate(task.actual_start_date)}
            {task.actual_end_date &&
              ` · Fin real: ${formatDate(task.actual_end_date)}`}
          </Text>
        )}

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
