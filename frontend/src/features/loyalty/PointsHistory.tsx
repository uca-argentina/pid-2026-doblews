import { Anchor, Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { formatQuantity } from "../../lib/format";
import { orderNumber } from "../purchase-orders/orderDisplay";
import { RULE_LABELS, comparedText, formatDay } from "./loyaltyDisplay";
import type { PointsEntryOut } from "./types";

interface PointsHistoryProps {
  firmId: number;
  entries: PointsEntryOut[];
}

/** Every entry behind the firm's level, newest first (HU-24).
 *
 * Each row has to explain its own number, which is the whole reason the entries
 * are stored instead of recomputed: the rule in words, the material and how
 * much of it arrived, and what that was compared against. A table from sm up
 * and cards below it, both rendered and one hidden by CSS. */
export function PointsHistory({ firmId, entries }: PointsHistoryProps) {
  return (
    <>
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={720}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Fecha</Table.Th>
                <Table.Th>Orden</Table.Th>
                <Table.Th>Obra</Table.Th>
                <Table.Th>Proveedor</Table.Th>
                <Table.Th>Material</Table.Th>
                <Table.Th>Por qué</Table.Th>
                <Table.Th ta="right">Puntos</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {entries.map((entry) => (
                <Table.Tr key={entry.id}>
                  <Table.Td>{formatDay(entry.earned_at)}</Table.Td>
                  <Table.Td>
                    <OrderLink firmId={firmId} entry={entry} />
                  </Table.Td>
                  <Table.Td>{entry.project.name}</Table.Td>
                  <Table.Td>{entry.supplier.name}</Table.Td>
                  <Table.Td>
                    {entry.resource.name}
                    <Text size="xs" c="dimmed">
                      {formatQuantity(entry.quantity)} {entry.unit.abbreviation}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    {RULE_LABELS[entry.rule]}
                    <Compared entry={entry} />
                  </Table.Td>
                  <Table.Td ta="right">
                    <Text fw={600}>+{entry.points}</Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {entries.map((entry) => (
          <Card key={entry.id} withBorder padding="sm" radius="md">
            <Stack gap={4}>
              <Group justify="space-between" align="baseline" wrap="nowrap">
                <OrderLink firmId={firmId} entry={entry} />
                <Text fw={700}>+{entry.points}</Text>
              </Group>
              <Text fw={600} size="sm">
                {entry.resource.name} · {formatQuantity(entry.quantity)}{" "}
                {entry.unit.abbreviation}
              </Text>
              <Text size="sm">{RULE_LABELS[entry.rule]}</Text>
              <Compared entry={entry} />
              <Text size="xs" c="dimmed">
                {entry.supplier.name} · {entry.project.name} ·{" "}
                {formatDay(entry.earned_at)}
              </Text>
            </Stack>
          </Card>
        ))}
      </Stack>
    </>
  );
}

function OrderLink({
  firmId,
  entry,
}: {
  firmId: number;
  entry: PointsEntryOut;
}) {
  return (
    <Anchor
      component={Link}
      to={`/firms/${firmId}/purchase-orders/${entry.order.id}`}
      size="sm"
    >
      {orderNumber(entry.order.number)}
    </Anchor>
  );
}

/** What the quantity was measured against, when there was anything. */
function Compared({ entry }: { entry: PointsEntryOut }) {
  const compared = comparedText(entry);
  if (!compared) return null;
  return (
    <Text size="xs" c="dimmed">
      {compared}
    </Text>
  );
}
