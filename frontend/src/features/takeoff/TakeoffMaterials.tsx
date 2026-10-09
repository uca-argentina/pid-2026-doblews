import { Box, Card, Stack, Table, Text } from "@mantine/core";
import { formatQuantity } from "../../lib/format";
import {
  RESOURCE_GROUP_LABELS,
  RESOURCE_TYPES,
  type ResourceType,
} from "../catalog/resourceTypes";
import type { TakeoffMaterialOut, TakeoffOut } from "./types";

interface TakeoffMaterialsProps {
  takeoff: TakeoffOut;
}

/** Everything the work needs and how much of it, with no money on it.
 *
 * This is the take-off of whoever may not see costs — the project client.
 * Those who may see them get the budget's groups on the same screen instead,
 * with a price and a subtotal next to each quantity, so the two never show
 * side by side.
 *
 * Grouped by kind since T-06 put hours into the recipes: a single table headed
 * "Materiales" listing "Oficial — 120 h" was wrong about its own contents, and
 * HU-10 asks for those hours to stay on this screen for the client too. */
export function TakeoffMaterials({ takeoff }: TakeoffMaterialsProps) {
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
        />
      ))}
    </Stack>
  );
}

/** One kind of resource: a table from sm up and cards below it, both rendered
 * and one hidden by CSS, like ResourceBrowser. */
function MaterialGroup({
  type,
  materials,
}: {
  type: ResourceType;
  materials: TakeoffMaterialOut[];
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
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {materials.map((material) => (
          <Card key={material.resource_id} withBorder padding="md" radius="md">
            <Text fw={600}>{material.name}</Text>
            <Text size="sm">
              {formatQuantity(material.quantity)} {material.unit.abbreviation}
            </Text>
          </Card>
        ))}
      </Stack>
    </Stack>
  );
}
