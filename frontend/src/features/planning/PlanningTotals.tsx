import { Group, Stack, Text } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import type { PlanningOut } from "./types";

/** What the planning adds up to: the take-off lines assigned to no task, and
 * the total.
 *
 * Renders nothing when the response carries no costs. The backend sends null
 * to whoever may not see them — the project client — so asking total_cost is
 * asking the backend, as TakeoffMaterials does.
 *
 * The unassigned amount is always shown, zero included: "everything is
 * planned" is an answer the architect is looking for, not an absence. */
export function PlanningTotals({ planning }: { planning: PlanningOut }) {
  if (planning.total_cost === null || planning.unassigned_cost === null) {
    return null;
  }

  return (
    <Stack gap={4} px={{ sm: "sm" }}>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          Cómputo sin asignar a ninguna tarea
        </Text>
        <Text size="sm">
          {formatMoney(planning.unassigned_cost, planning.currency)}
        </Text>
      </Group>
      <Group justify="space-between">
        <Text fw={600}>Total estimado</Text>
        <Text fw={700} size="lg">
          {formatMoney(planning.total_cost, planning.currency)}
        </Text>
      </Group>
      {/* Why this total and the budget's can be a few cents apart (ADR-009
          section 8). Said here because it is the one number on this screen a
          careful reader will compare against another one. */}
      <Text size="xs" c="dimmed">
        A precios de referencia de hoy. Cada tarea se redondea por separado, así
        que el total puede diferir en centavos del de Presupuesto.
      </Text>
    </Stack>
  );
}
