import { Card, Group, Stack, Text } from "@mantine/core";
import dayjs from "dayjs";
import { formatMoney } from "../../lib/format";
import type { BudgetOut } from "./types";

/** What the work costs today, and how old the prices behind that number are.
 *
 * A card and not a closing line under the groups: it opens the take-off, above
 * everything that adds up to it, so it has to read as the answer rather than
 * as the last row of a table that has not been shown yet. */
export function BudgetTotal({ budget }: { budget: BudgetOut }) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" wrap="nowrap">
          <Text fw={600}>Total estimado</Text>
          <Text fw={700} size="xl">
            {formatMoney(budget.total, budget.currency)}
          </Text>
        </Group>
        {/* ADR-005 section 5: the prices are live, so the total moves when the
            catalogue does. Saying how old the oldest one is keeps the number
            honest, and it is the figure that ends up in front of a client. */}
        {budget.prices_as_of && (
          <Text size="xs" c="dimmed">
            Precios de referencia al{" "}
            {dayjs(budget.prices_as_of).format("DD/MM/YYYY")}. Es una
            estimación: no incluye costos indirectos, gastos generales,
            beneficio ni IVA.
          </Text>
        )}
      </Stack>
    </Card>
  );
}
