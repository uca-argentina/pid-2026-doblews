import { Badge, Text } from "@mantine/core";
import { EMPTY } from "../projects/projectFields";
import { formatSlack } from "./taskFields";
import type { TaskOut } from "./types";

/** A task's slack as the table and the card show it. A critical task gets a
 * red badge, which is what makes the critical path stand out in the list
 * (HU-14); any other slack is plain text, and a finished task a dash.
 *
 * `labelled` says what the number is, for the card: the table has a column
 * heading for that, a phone screen does not. */
export function SlackBadge({
  task,
  labelled = false,
}: {
  task: TaskOut;
  labelled?: boolean;
}) {
  if (task.is_critical) {
    return (
      <Badge color="red" variant="light">
        Crítica
      </Badge>
    );
  }
  return (
    <Text size="sm" c={task.slack_days === null ? "dimmed" : undefined}>
      {task.slack_days === null
        ? EMPTY
        : `${labelled ? "Holgura: " : ""}${formatSlack(task)}`}
    </Text>
  );
}
