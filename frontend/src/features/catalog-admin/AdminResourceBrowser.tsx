import { useMemo, useState, type ReactNode } from "react";
import {
  Alert,
  Box,
  Card,
  Center,
  Group,
  Loader,
  Select,
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

// "all" is the default, un-filtered view; the rest mirror resource.type.
type TypeFilter = "all" | ResourceType;

const TYPE_FILTER_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "Todos los tipos" },
  { value: "material", label: "Material" },
  { value: "labor", label: "Mano de obra" },
  { value: "equipment", label: "Equipo" },
];

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
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");

  const visible = useMemo(
    () =>
      resources?.filter(
        (resource) =>
          matchesSearch(resource.name, query) &&
          (typeFilter === "all" || resource.type === typeFilter),
      ) ?? [],
    [resources, query, typeFilter],
  );

  return (
    <Stack gap="sm">
      <Group gap="sm" align="flex-end" grow wrap="wrap">
        <TextInput
          placeholder="Buscar recurso por nombre"
          aria-label="Buscar recurso"
          value={query}
          onChange={(event) => setQuery(event.currentTarget.value)}
        />
        <Select
          aria-label="Filtrar por tipo"
          data={TYPE_FILTER_OPTIONS}
          value={typeFilter}
          onChange={(value) => setTypeFilter((value as TypeFilter) ?? "all")}
          allowDeselect={false}
          maw={{ sm: 220 }}
        />
      </Group>

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar los recursos. Probá de nuevo en un momento.
        </Alert>
      )}

      {resources && visible.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="md">
          {resources.length === 0
            ? "El catálogo todavía no tiene recursos."
            : "Ningún recurso coincide con la búsqueda."}
        </Text>
      )}

      {visible.length > 0 && (
        <>
          <Box visibleFrom="sm">
            <Table verticalSpacing="sm" highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Recurso</Table.Th>
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
