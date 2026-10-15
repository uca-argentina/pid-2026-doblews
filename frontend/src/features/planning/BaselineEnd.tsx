import { Badge, Group, Text } from "@mantine/core";
import { formatDate } from "../projects/projectFields";
import { isOverdue } from "./progress";
import type { TaskOut } from "./types";

/** The end fixed for a task, with "Atrasada" once it has passed and the task
 * is not finished. Shared by ProgressTable and ProgressCard. */
export function BaselineEnd({ task, today }: { task: TaskOut; today: string }) {
  if (task.baseline_end_date === null) {
    return (
      <Text size="sm" c="dimmed">
        Sin fijar
      </Text>
    );
  }
  return (
    <Group gap="xs" wrap="nowrap">
      <Text size="sm" style={{ whiteSpace: "nowrap" }}>
        {formatDate(task.baseline_end_date)}
      </Text>
      {isOverdue(task, today) && (
        <Badge color="red" variant="light">
          Atrasada
        </Badge>
      )}
    </Group>
  );
}
