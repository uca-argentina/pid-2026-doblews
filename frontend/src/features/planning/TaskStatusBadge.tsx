import { Badge } from "@mantine/core";
import { STATUS_COLORS, STATUS_LABELS } from "./taskStatus";
import type { TaskStatus } from "./types";

/** A task's status, as the table and the card both show it. */
export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge variant="light" color={STATUS_COLORS[status]}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
