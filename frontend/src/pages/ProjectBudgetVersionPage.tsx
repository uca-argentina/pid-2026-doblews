import {
  Alert,
  Anchor,
  Badge,
  Center,
  Divider,
  Group,
  Loader,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import dayjs from "dayjs";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import type { BudgetVersionOut } from "../features/budget-versions/types";
import { useBudgetVersion } from "../features/budget-versions/useBudgetVersions";
import { BudgetGroupSection } from "../features/budget/BudgetGroupSection";
import { useBudgetAccess } from "../features/budget/useBudgetAccess";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { formatMoney, formatQuantity } from "../lib/format";

/** One saved version, read-only — and read-only all the way down: there is no
 * endpoint that could change it, so there is nothing here to edit with.
 *
 * The groups render through the same component as the take-off's live budget,
 * so a version and the numbers it came from read identically. What differs is the date next to
 * the prices: here it is when they were current, not today. */
export function ProjectBudgetVersionPage() {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const { versionId: param = "" } = useParams<{ versionId: string }>();
  const canView = useBudgetAccess();

  const versionId = Number(param);
  const {
    data: version,
    isLoading,
    isError,
  } = useBudgetVersion(firm.id, project.id, versionId);

  const versionsPath = `/firms/${firm.id}/projects/${project.id}/budget`;

  if (!canView) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver los costos.
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !version) {
    return (
      <Stack gap="md">
        <BackLink to={versionsPath} />
        <Alert color="red" variant="light">
          No encontramos ese presupuesto guardado.
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack gap="xl">
      <Stack gap="md">
        <BackLink to={versionsPath} />
        <PageHeader
          title={`Versión v${version.version_number}`}
          description={version.note ?? undefined}
          order={4}
          action={<Badge variant="light">Solo lectura</Badge>}
        />
        <Text size="sm" c="dimmed">
          Guardada el {dayjs(version.created_at).format("DD/MM/YYYY")} a las{" "}
          {dayjs(version.created_at).format("HH:mm")} por{" "}
          {version.created_by_name}.
        </Text>
      </Stack>

      {version.groups
        .filter((group) => group.items.length > 0)
        .map((group) => (
          <BudgetGroupSection
            key={group.type}
            group={group}
            currency={version.currency}
          />
        ))}

      <Stack gap="xs">
        <Divider />
        <Group justify="space-between" px={{ sm: "sm" }}>
          <Text fw={600}>Total general</Text>
          <Text fw={700} size="xl">
            {formatMoney(version.total, version.currency)}
          </Text>
        </Group>
        <Text size="xs" c="dimmed">
          Precios de referencia al{" "}
          {dayjs(version.prices_as_of).format("DD/MM/YYYY")}, que son los que
          tenía el catálogo cuando se guardó. El cómputo de hoy puede dar
          distinto: esta versión no se mueve.
        </Text>
      </Stack>

      <FrozenLines version={version} />
    </Stack>
  );
}

function BackLink({ to }: { to: string }) {
  return (
    <div>
      <Anchor component={Link} to={to} size="sm" c="dimmed">
        ← Presupuestos
      </Anchor>
    </div>
  );
}

/** The take-off that produced these numbers, so a reader can see what was
 * measured and not only what it cost. One row per line, notes included: that is
 * the granularity the version stored, and what "Cargar" would bring back. */
function FrozenLines({ version }: { version: BudgetVersionOut }) {
  return (
    <Stack gap="sm">
      <Text fw={600} size="sm">
        Cómputo de esta versión
      </Text>
      <Table verticalSpacing="sm">
        <Table.Tbody>
          {version.lines.map((line, index) => (
            <Table.Tr key={`${line.recipe_id}-${index}`}>
              <Table.Td>
                <Text size="sm" fw={500}>
                  {line.recipe_name}
                </Text>
                {line.note && (
                  <Text size="sm" c="dimmed">
                    {line.note}
                  </Text>
                )}
              </Table.Td>
              <Table.Td ta="right">
                <Text size="sm">{formatQuantity(line.quantity)}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
