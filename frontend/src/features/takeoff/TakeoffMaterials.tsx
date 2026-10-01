import { Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import dayjs from "dayjs";
import { formatMoney, formatQuantity } from "../../lib/format";
import {
  RESOURCE_GROUP_LABELS,
  RESOURCE_TYPES,
  type ResourceType,
} from "../catalog/resourceTypes";
import type { TakeoffMaterialOut, TakeoffOut } from "./types";

interface TakeoffMaterialsProps {
  takeoff: TakeoffOut;
}

/** The answer HU-5 promises: everything the work needs, how much of it, and
 * what it costs.
 *
 * Grouped by kind since T-06 put hours into the recipes: a single table headed
 * "Materiales" listing "Oficial — 120 h" was wrong about its own contents, and
 * HU-10 asks for those hours to stay on this screen for the client too, so the
 * fix is to group them rather than to hide them. HU-11's budget is the same
 * three groups with their prices and subtotals, behind project.cost.view.
 *
 * The cost column exists only when the response carries a total. The backend
 * sends null to whoever may not see costs — the project client — so asking
 * total_cost is asking the backend, and a client's screen shows quantities
 * with no empty column where the money would be.
 *
 * The total sits under every group, since it belongs to none of them. */
export function TakeoffMaterials({ takeoff }: TakeoffMaterialsProps) {
  const showsCost = takeoff.total_cost !== null;

  const groups = RESOURCE_TYPES.map((type) => ({
    type,
    materials: takeoff.materials.filter((material) => material.type === type),
  })).filter((group) => group.materials.length > 0);

  return (
    <Stack gap="lg">
      {groups.map((group) => (
        <MaterialGroup
          key={group.type}
          type={group.type}
          materials={group.materials}
          showsCost={showsCost}
        />
      ))}

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

/** One kind of resource: a table from sm up and cards below it, both rendered
 * and one hidden by CSS, like ResourceBrowser. */
function MaterialGroup({
  type,
  materials,
  showsCost,
}: {
  type: ResourceType;
  materials: TakeoffMaterialOut[];
  showsCost: boolean;
}) {
  return (
    <Stack gap="xs">
      <Text fw={600} size="sm">
        {RESOURCE_GROUP_LABELS[type]}
      </Text>

      <Box visibleFrom="sm">
        <Table verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Recurso</Table.Th>
              <Table.Th ta="right">Cantidad</Table.Th>
              {showsCost && <Table.Th ta="right">Costo estimado</Table.Th>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {materials.map((material) => (
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
        {materials.map((material) => (
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
    </Stack>
  );
}
