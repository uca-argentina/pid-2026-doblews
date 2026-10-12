import { Group, Progress, Text } from "@mantine/core";
import { STATUS_COLORS } from "./taskStatus";
import type { TaskOut } from "./types";

/** How much of a task is done, as the table and the card show it (HU-16): a
 * bar and its number.
 *
 * The bar takes the colour of the task's status, like its badge and its bar
 * in the Gantt, so a finished task reads as finished here too. */
export function TaskProgress({ task }: { task: TaskOut }) {
  return (
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
  );
}
