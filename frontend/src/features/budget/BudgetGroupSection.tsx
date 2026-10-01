import { Box, Card, Group, Stack, Table, Text, Title } from "@mantine/core";
import { formatMoney, formatQuantity } from "../../lib/format";
import { RESOURCE_GROUP_LABELS } from "../catalog/resourceTypes";
import type { BudgetSectionGroup } from "./types";

interface BudgetGroupSectionProps {
  group: BudgetSectionGroup;
  currency: string;
}

/** One of the budget's three groups: its resources, and what they add up to.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS,
 * like TakeoffMaterials. The table is what HU-11 rules out on a phone — four
 * numeric columns at 375px either scroll sideways or shrink past reading — so
 * the card carries the same four facts stacked instead.
 *
 * The subtotal sits under both, since it belongs to neither layout. */
export function BudgetGroupSection({
  group,
  currency,
}: BudgetGroupSectionProps) {
  return (
    <Stack gap="sm">
      <Title order={4}>{RESOURCE_GROUP_LABELS[group.type]}</Title>

      <Box visibleFrom="sm">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Recurso</Table.Th>
              <Table.Th ta="right">Cantidad</Table.Th>
              <Table.Th ta="right">Precio unitario</Table.Th>
              <Table.Th ta="right">Subtotal</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {group.items.map((item) => (
              <Table.Tr key={item.resource_id}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {item.name}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm">
                    {formatQuantity(item.quantity)} {item.unit_abbreviation}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm" c="dimmed">
                    {formatMoney(item.unit_price, currency)} /{" "}
                    {item.unit_abbreviation}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm">{formatMoney(item.subtotal, currency)}</Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {group.items.map((item) => (
          <Card key={item.resource_id} withBorder padding="md" radius="md">
            <Text fw={600}>{item.name}</Text>
            <Text size="sm" c="dimmed">
              {formatQuantity(item.quantity)} {item.unit_abbreviation} ×{" "}
              {formatMoney(item.unit_price, currency)}
            </Text>
            <Group justify="flex-end">
              <Text size="sm" fw={500}>
                {formatMoney(item.subtotal, currency)}
              </Text>
            </Group>
          </Card>
        ))}
      </Stack>

      <Group justify="space-between" px={{ sm: "sm" }}>
        <Text size="sm" fw={500} c="dimmed">
          Subtotal {RESOURCE_GROUP_LABELS[group.type].toLowerCase()}
        </Text>
        <Text fw={600}>{formatMoney(group.subtotal, currency)}</Text>
      </Group>
    </Stack>
  );
}
