import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import dayjs from "dayjs";
import { formatMoney, matchesSearch } from "../../lib/format";
import { useCurrentFirm } from "../firms/firmContext";
import type { ResourceOut } from "./types";
import { useResources } from "./useCatalog";

/** The date of the oldest price among these, or null when there are none.
 *
 * The oldest and not the newest: "precios de referencia al <fecha>" is a
 * promise about every number on the screen, and it only holds for the one that
 * has gone longest without an update. */
function oldestPriceDate(resources: ResourceOut[]): string | null {
  if (resources.length === 0) return null;
  const oldest = resources.reduce((a, b) =>
    dayjs(a.price_updated_at).isBefore(b.price_updated_at) ? a : b,
  );
  return dayjs(oldest.price_updated_at).format("DD/MM/YYYY");
}

/** Search the catalogue's materials and read their reference prices.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS,
 * like ProjectsPage. Read-only: nothing here is added to a work, because what
 * a work computes is recipes (ADR-003 section 1), so unlike RecipeBrowser this
 * takes no action. */
export function ResourceBrowser() {
  const { firm } = useCurrentFirm();
  const { data: resources, isLoading, isError } = useResources(firm.id);
  const [query, setQuery] = useState("");

  const visible = useMemo(
    () =>
      resources?.filter((resource) => matchesSearch(resource.name, query)) ??
      [],
    [resources, query],
  );
  // Over the whole catalogue, not what the search left: the date describes the
  // prices, and typing in the search box should not move it.
  const pricesAsOf = resources ? oldestPriceDate(resources) : null;

  return (
    <Stack gap="sm">
      <TextInput
        placeholder="Buscar material por nombre"
        aria-label="Buscar material"
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar los materiales. Probá de nuevo en un momento.
        </Alert>
      )}

      {resources && visible.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="md">
          {resources.length === 0
            ? "El catálogo todavía no tiene materiales."
            : "Ningún material coincide con la búsqueda."}
        </Text>
      )}

      {visible.length > 0 && (
        <>
          <Box visibleFrom="sm">
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Material</Table.Th>
                  <Table.Th>Unidad</Table.Th>
                  <Table.Th ta="right">Precio de referencia</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {visible.map((resource) => (
                  <Table.Tr key={resource.id}>
                    <Table.Td>
                      <Text size="sm" fw={500}>
                        {resource.name}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{resource.unit.abbreviation}</Text>
                    </Table.Td>
                    <Table.Td ta="right">
                      <Text size="sm">
                        {formatMoney(
                          resource.reference_price,
                          resource.currency,
                        )}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Box>

          <Stack gap="sm" hiddenFrom="sm">
            {visible.map((resource) => (
              <Card key={resource.id} withBorder padding="md" radius="md">
                <Text fw={600}>{resource.name}</Text>
                <Group justify="space-between" gap="xs" wrap="nowrap">
                  <Text size="sm" c="dimmed">
                    por {resource.unit.abbreviation}
                  </Text>
                  <Text size="sm" fw={500}>
                    {formatMoney(resource.reference_price, resource.currency)}
                  </Text>
                </Group>
              </Card>
            ))}
          </Stack>
        </>
      )}

      {pricesAsOf && (
        <Text size="xs" c="dimmed">
          Precios de referencia al {pricesAsOf}. Son los mismos para todos los
          estudios.
        </Text>
      )}
    </Stack>
  );
}
