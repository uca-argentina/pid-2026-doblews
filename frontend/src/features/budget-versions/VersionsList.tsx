import type { ReactNode } from "react";
import { Anchor, Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { formatMoney } from "../../lib/format";
import type { BudgetVersionSummary } from "./types";

interface VersionsListProps {
  versions: BudgetVersionSummary[];
  /** Where one version's own screen lives, given its id. */
  hrefFor: (versionId: number) => string;
  /** The "Cargar" action per row, when the caller may replace the draft. */
  renderActions?: (version: BudgetVersionSummary) => ReactNode;
}

/** The saved versions of a work: a table from sm up and cards below it, both
 * rendered and one hidden by CSS, like every other listing here.
 *
 * The number is the link and the only one in the row: a whole clickable row
 * cannot be reached with a keyboard. */
export function VersionsList({
  versions,
  hrefFor,
  renderActions,
}: VersionsListProps) {
  return (
    <>
      <Box visibleFrom="sm">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Versión</Table.Th>
              <Table.Th>Guardada</Table.Th>
              <Table.Th>Por</Table.Th>
              <Table.Th ta="right">Total</Table.Th>
              {renderActions && <Table.Th w={120} />}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {versions.map((version) => (
              <Table.Tr key={version.id}>
                <Table.Td>
                  <Anchor
                    component={Link}
                    to={hrefFor(version.id)}
                    fw={600}
                    underline="never"
                  >
                    v{version.version_number}
                  </Anchor>
                  {version.note && (
                    <Text size="sm" c="dimmed">
                      {version.note}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td>
                  <Text size="sm">
                    {dayjs(version.created_at).format("DD/MM/YYYY HH:mm")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{version.created_by_name}</Text>
                </Table.Td>
                <Table.Td ta="right">
                  <Text size="sm">
                    {formatMoney(version.total, version.currency)}
                  </Text>
                </Table.Td>
                {renderActions && (
                  <Table.Td ta="right">{renderActions(version)}</Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {versions.map((version) => (
          <Card key={version.id} withBorder padding="md" radius="md">
            <Stack gap={4}>
              <Group justify="space-between" gap="xs" wrap="nowrap">
                <Anchor
                  component={Link}
                  to={hrefFor(version.id)}
                  fw={600}
                  underline="never"
                >
                  v{version.version_number}
                </Anchor>
                <Text fw={600}>
                  {formatMoney(version.total, version.currency)}
                </Text>
              </Group>

              {version.note && (
                <Text size="sm" c="dimmed" truncate>
                  {version.note}
                </Text>
              )}

              <Group justify="space-between" gap="xs" wrap="nowrap">
                <Text size="sm" c="dimmed">
                  {dayjs(version.created_at).format("DD/MM/YYYY")} ·{" "}
                  {version.created_by_name}
                </Text>
                {renderActions?.(version)}
              </Group>
            </Stack>
          </Card>
        ))}
      </Stack>
    </>
  );
}
