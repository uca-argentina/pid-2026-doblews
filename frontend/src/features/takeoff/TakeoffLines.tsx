import type { ReactNode } from "react";
import { Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import { formatQuantity } from "../../lib/format";
import type { TakeoffLineOut } from "./types";

interface TakeoffLinesProps {
  lines: TakeoffLineOut[];
  /** What each line offers to do: edit and remove, for those who may manage
   * the take-off. Omitted for everyone else, and then no actions column. */
  renderActions?: (line: TakeoffLineOut) => ReactNode;
}

/** What was loaded onto the work: each recipe, how much of it, the note that
 * tells two lines of the same recipe apart, and the task of the planning it is
 * assigned to (HU-13).
 *
 * The order is the backend's — recipe, then note — so two storeys of the same
 * wall sit next to each other and nothing reshuffles between reloads. */
export function TakeoffLines({ lines, renderActions }: TakeoffLinesProps) {
  return (
    <>
      <Box visibleFrom="sm">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Receta</Table.Th>
              <Table.Th>Nota</Table.Th>
              <Table.Th>Tarea</Table.Th>
              <Table.Th ta="right">Cantidad</Table.Th>
              {/* No heading, like the roster's actions column: the menu's own
                  label says what it does. */}
              {renderActions && <Table.Th w={60} />}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {lines.map((line) => (
              <Table.Tr key={line.id}>
                <Table.Td>
                  <Text size="sm" fw={500}>
                    {line.recipe.name}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={line.note ? undefined : "dimmed"}>
                    {line.note ?? "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c={line.task ? undefined : "dimmed"}>
                    {line.task?.name ?? "Sin asignar"}
                  </Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm" style={{ whiteSpace: "nowrap" }}>
                    {formatQuantity(line.quantity)}{" "}
                    {line.recipe.unit.abbreviation}
                  </Text>
                </Table.Td>
                {renderActions && <Table.Td>{renderActions(line)}</Table.Td>}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {lines.map((line) => (
          <Card key={line.id} withBorder padding="md" radius="md">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <div>
                <Text fw={600}>{line.recipe.name}</Text>
                {line.note && (
                  <Text size="sm" c="dimmed">
                    {line.note}
                  </Text>
                )}
                <Text size="sm" mt={4}>
                  {formatQuantity(line.quantity)}{" "}
                  {line.recipe.unit.abbreviation}
                </Text>
                <Text size="xs" c="dimmed">
                  {line.task ? `Tarea: ${line.task.name}` : "Sin asignar"}
                </Text>
              </div>
              {renderActions?.(line)}
            </Group>
          </Card>
        ))}
      </Stack>
    </>
  );
}
