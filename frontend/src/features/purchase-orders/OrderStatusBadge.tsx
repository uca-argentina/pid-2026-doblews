import { Badge } from "@mantine/core";
import { STATUS_COLORS, STATUS_LABELS } from "./orderDisplay";
import type { OrderStatus } from "./types";

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return (
    <Badge color={STATUS_COLORS[status]} variant="light">
      {STATUS_LABELS[status]}
    </Badge>
  );
}
