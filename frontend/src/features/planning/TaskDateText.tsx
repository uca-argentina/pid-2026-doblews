import { Text } from "@mantine/core";
import type { TaskDate } from "./taskFields";

/** One end of a task in the listing. An actual date reads as plain text; a
 * planned one is dimmed, since it is what is expected rather than what
 * happened, and moves by itself when something upstream is late (HU-14). */
export function TaskDateText({ date }: { date: TaskDate }) {
  return (
    <Text
      span
      size="sm"
      c={date.actual ? undefined : "dimmed"}
      title={date.actual ? "Real" : "Prevista"}
      style={{ whiteSpace: "nowrap" }}
    >
      {date.label}
    </Text>
  );
}
