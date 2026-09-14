import { Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import dayjs from "dayjs";
import { formatMoney, formatQuantity } from "../../lib/format";
import type { TakeoffOut } from "./types";

interface TakeoffMaterialsProps {
  takeoff: TakeoffOut;
}

/** The answer HU-5 promises: every material the work needs, how much of it, and
 * what it costs.
 *
 * The cost column exists only when the response carries a total. The backend
 * sends null to whoever may not see costs — the project client — so asking
 * total_cost is asking the backend, and a client's screen shows quantities
 * with no empty column where the money would be.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS,
 * like ResourceBrowser. The total sits under both, since it belongs to neither
 * layout in particular. */
export function TakeoffMaterials({ takeoff }: TakeoffMaterialsProps) {
  const showsCost = takeoff.total_cost !== null;

  return (
    <Stack gap="sm">
      <Box visibleFrom="sm">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Material</Table.Th>
              <Table.Th ta="right">Cantidad</Table.Th>
              {showsCost && <Table.Th ta="right">Costo estimado</Table.Th>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {takeoff.materials.map((material) => (
              <Table.Tr key={material.resource_id}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {material.name}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm">
                    {formatQuantity(material.quantity)}{" "}
                    {material.unit.abbreviation}
                  </Text>
                </Table.Td>
                {showsCost && (
                  <Table.Td ta="right">
                    <Text size="sm">
                      {material.cost !== null &&
                        formatMoney(material.cost, material.currency)}
                    </Text>
                  </Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {takeoff.materials.map((material) => (
          <Card key={material.resource_id} withBorder padding="md" radius="md">
            <Text fw={600}>{material.name}</Text>
            <Group justify="space-between" gap="xs" wrap="nowrap">
              <Text size="sm">
                {formatQuantity(material.quantity)} {material.unit.abbreviation}
              </Text>
              {material.cost !== null && (
                <Text size="sm" fw={500}>
                  {formatMoney(material.cost, material.currency)}
                </Text>
              )}
            </Group>
          </Card>
        ))}
      </Stack>

      {takeoff.total_cost !== null && (
        <Group justify="space-between" px={{ sm: "sm" }}>
          <Text fw={600}>Total estimado</Text>
          <Text fw={700} size="lg">
            {formatMoney(takeoff.total_cost, takeoff.currency)}
          </Text>
        </Group>
      )}

      {/* ADR-005 section 5: prices are live, so a work's cost changes when
          they do. Saying how old the oldest one is keeps that honest. Only
          next to costs: a client who sees no money needs no price date. */}
      {showsCost && takeoff.prices_as_of && (
        <Text size="xs" c="dimmed">
          Precios de referencia al{" "}
          {dayjs(takeoff.prices_as_of).format("DD/MM/YYYY")}. Se actualizan con
          el catálogo, así que el costo de la obra puede cambiar sin que nadie
          la edite.
        </Text>
      )}
    </Stack>
  );
}
