import { useMemo, useState, type ReactNode } from "react";
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
import { useAdminResources } from "./useCatalogAdmin";
import type { ResourceOut, ResourceType } from "./types";

/** Spanish labels for resource.type (app/models/catalog.py's
 * RESOURCE_TYPE_CHECK). Sprint 1 only seeds "material"; the other two exist
 * for the day the team loads labour or equipment. */
const TYPE_LABELS: Record<ResourceType, string> = {
  material: "Material",
  labor: "Mano de obra",
  equipment: "Equipo",
};

interface AdminResourceBrowserProps {
  /** What each row offers to do with its material. Same render-prop contract
   * as AdminRecipeBrowser/RecipeBrowser's renderAction. */
  renderAction?: (resource: ResourceOut) => ReactNode;
}

/** Search and list the catalogue's materials for support to administer
 * (HU-8).
 *
 * Deliberately not ResourceBrowser (HU-4's read-only, firm-scoped one): this
 * needs its own data source (the platform-scoped admin endpoint, not
 * /firms/{firmId}/catalog/resources) and shows price_updated_at *per row*
 * ("desde cuándo rige ese precio"), where ResourceBrowser instead computes
 * one aggregate "precios de referencia al <fecha>" footer over the whole
 * visible list — a different question than this screen asks. */
export function AdminResourceBrowser({
  renderAction,
}: AdminResourceBrowserProps) {
  const { data: resources, isLoading, isError } = useAdminResources();
  const [query, setQuery] = useState("");

  const visible = useMemo(
    () =>
      resources?.filter((resource) => matchesSearch(resource.name, query)) ??
      [],
    [resources, query],
  );

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
                  <Table.Th>Tipo</Table.Th>
                  <Table.Th>Unidad</Table.Th>
                  <Table.Th ta="right">Precio de referencia</Table.Th>
                  <Table.Th>Vigente desde</Table.Th>
                  <Table.Th w={60} />
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
                      <Text size="sm">
                        {TYPE_LABELS[resource.type as ResourceType]}
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
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {dayjs(resource.price_updated_at).format("DD/MM/YYYY")}
                      </Text>
                    </Table.Td>
                    <Table.Td>{renderAction?.(resource)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Box>

          <Stack gap="sm" hiddenFrom="sm">
            {visible.map((resource) => (
              <Card key={resource.id} withBorder padding="md" radius="md">
                <Group justify="space-between" align="flex-start" wrap="nowrap">
                  <Text fw={600}>{resource.name}</Text>
                  <Group gap="xs" wrap="nowrap">
                    <Text size="sm" fw={500}>
                      {formatMoney(resource.reference_price, resource.currency)}
                    </Text>
                    {renderAction?.(resource)}
                  </Group>
                </Group>
                <Text size="sm" c="dimmed">
                  {TYPE_LABELS[resource.type as ResourceType]} · por{" "}
                  {resource.unit.abbreviation}
                </Text>
                <Text size="xs" c="dimmed">
                  Vigente desde{" "}
                  {dayjs(resource.price_updated_at).format("DD/MM/YYYY")}
                </Text>
              </Card>
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
