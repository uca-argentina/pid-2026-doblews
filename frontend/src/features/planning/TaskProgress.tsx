import { Badge, Group, Progress, Stack, Text } from "@mantine/core";
import { STANDING_COLORS, STANDING_LABELS } from "./progress";
import { STATUS_COLORS } from "./taskStatus";
import type { TaskOut } from "./types";

/** How much of a task is done against how much was planned by today, as the
 * table and the card show it (HU-16).
 *
 * The bar takes the colour of the task's status, like its badge and its bar
 * in the Gantt, so a finished task reads as finished here too.
 *
 * Under it, the comparison — only once there is one. With no planning fixed
 * on the work nothing is said, and the block above the list is what asks for
 * it. With one fixed, a task loaded since has no baseline and says so: it is
 * out of the comparison until the planning is fixed again. */
export function TaskProgress({
  task,
  baselineFixed,
}: {
  task: TaskOut;
  /** Whether the work has a planning fixed at all. */
  baselineFixed: boolean;
}) {
  return (
    <Stack gap={4}>
      <Group gap="xs" wrap="nowrap">
        <Progress
          value={task.progress_percent}
          color={STATUS_COLORS[task.status]}
          w={64}
          size="sm"
          aria-label={`Avance de ${task.name}`}
        />
        <Text size="sm" style={{ whiteSpace: "nowrap" }}>
          {task.progress_percent}%
        </Text>
      </Group>

      {task.progress_standing !== null ? (
        <Group gap={6} wrap="nowrap">
          <Text size="xs" c="dimmed" style={{ whiteSpace: "nowrap" }}>
            Planificado {task.planned_progress_percent}%
          </Text>
          <Badge
            size="sm"
            variant="light"
            color={STANDING_COLORS[task.progress_standing]}
          >
            {STANDING_LABELS[task.progress_standing]}
          </Badge>
        </Group>
      ) : (
        baselineFixed && (
          <Badge size="sm" variant="outline" color="gray">
            Sin fijar
          </Badge>
        )
      )}
    </Stack>
  );
}
