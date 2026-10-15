import { Group, Text } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import type { PlanningOut } from "./types";

/** What the take-off lines assigned to no task add up to: the part of the work
 * that is costed and not yet planned.
 *
 * The work's total is not here. It lives on the take-off, the one screen with
 * the live budget; this one answers what each task costs and how much is left
 * outside all of them.
 *
 * Renders nothing when the response carries no costs. The backend sends null
 * to whoever may not see them — the project client.
 *
 * Always shown, zero included: "everything is planned" is an answer the
 * architect is looking for, not an absence. */
export function UnassignedCost({ planning }: { planning: PlanningOut }) {
  if (planning.unassigned_cost === null) {
    return null;
  }

  return (
    <Group justify="space-between" px={{ sm: "sm" }}>
      <Text size="sm" c="dimmed">
        Cómputo sin asignar a ninguna tarea
      </Text>
      <Text size="sm">
        {formatMoney(planning.unassigned_cost, planning.currency)}
      </Text>
    </Group>
  );
}
