import { Button, Card, Group, Stack, Text } from "@mantine/core";
import { BaselineEnd } from "./BaselineEnd";
import { formatPlanned, takesProgress } from "./progress";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface ProgressCardProps {
  task: TaskOut;
  today: string;
  /** Opens the form that records this task's progress, for those who may
   * manage the planning. */
  onRecord?: (task: TaskOut) => void;
}

/** One task's progress on a phone. Same data as a row of ProgressTable,
 * stacked, so 375px needs no horizontal scrolling. Each value says what it
 * is, since there is no column heading to do it. */
export function ProgressCard({ task, today, onRecord }: ProgressCardProps) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={6}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600}>{task.name}</Text>
          <TaskStatusBadge status={task.status} />
        </Group>

        <Group justify="space-between" wrap="nowrap" gap="xs">
          <Text size="sm" c="dimmed">
            Fin planificado
          </Text>
          <BaselineEnd task={task} today={today} />
        </Group>

        <Group justify="space-between" wrap="nowrap" gap="xs">
          <Text size="sm">Real: {task.progress_percent}%</Text>
          <Text size="sm">Planificado: {formatPlanned(task)}</Text>
        </Group>

        {onRecord && takesProgress(task) && (
          <Group justify="flex-end" mt={4}>
            <Button size="xs" variant="default" onClick={() => onRecord(task)}>
              Registrar avance
            </Button>
          </Group>
        )}
      </Stack>
    </Card>
  );
}
