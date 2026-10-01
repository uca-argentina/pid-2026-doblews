import {
  Alert,
  Anchor,
  Button,
  Card,
  Center,
  Divider,
  Group,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { useState } from "react";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { BudgetGroupSection } from "../features/budget/BudgetGroupSection";
import { toSectionGroups } from "../features/budget/types";
import type { BudgetOut } from "../features/budget/types";
import { useBudget } from "../features/budget/useBudget";
import { SaveVersionModal } from "../features/budget-versions/SaveVersionModal";
import { useBudgetAccess } from "../features/budget/useBudgetAccess";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { formatMoney } from "../lib/format";

/** HU-11: what the work is going to cost, and where the money goes.
 *
 * Everything on this screen is computed from the take-off, so there is nothing
 * to edit here — the way to change the budget is to change the cómputo, which
 * is what the empty state links to. It is the draft HU-12 will freeze. */
export function ProjectBudgetPage() {
  const { firm } = useCurrentFirm();
  const { project, can } = useCurrentProject();
  const canView = useBudgetAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL — the
    // project client, in practice. The backend refuses the read anyway.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver los costos.
      </Alert>
    );
  }

  return (
    <BudgetView
      firmId={firm.id}
      projectId={project.id}
      canManage={can("project.budget.manage")}
    />
  );
}

function BudgetView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: budget, isLoading, isError } = useBudget(firmId, projectId);
  const [saving, setSaving] = useState(false);

  const versionsPath = `/firms/${firmId}/projects/${projectId}/budget/versions`;

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !budget) {
    return (
      <Alert color="red" variant="light">
        No pudimos cargar el presupuesto. Probá de nuevo en un momento.
      </Alert>
    );
  }

  // Every group arrives, empty ones included. Nothing at all means the work has
  // no lines, which is the empty state; a group that is merely empty — a work
  // with no equipment — is left out rather than shown as a heading over zero.
  const groups = toSectionGroups(budget.groups).filter(
    (group) => group.items.length > 0,
  );

  if (groups.length === 0) {
    return (
      <EmptyBudget
        takeoffPath={`/firms/${firmId}/projects/${projectId}/takeoff`}
      />
    );
  }

  return (
    <Stack gap="xl">
      <PageHeader
        title="Presupuesto estimado"
        description="Calculado con el cómputo de la obra y los precios de referencia del catálogo. Cambia solo cuando cambia alguno de los dos."
        order={4}
        action={
          canManage ? (
            <Button onClick={() => setSaving(true)}>Guardar versión</Button>
          ) : undefined
        }
      />

      {/* The way into HU-12, and not a fifth tab: versions belong to this
          section, and a fifth tab at 375px costs more than it explains. */}
      <div>
        <Anchor component={Link} to={versionsPath} size="sm">
          Ver versiones guardadas
        </Anchor>
      </div>

      {groups.map((group) => (
        <BudgetGroupSection
          key={group.type}
          group={group}
          currency={budget.currency}
        />
      ))}

      <Stack gap="xs">
        <Divider />
        <Group justify="space-between" px={{ sm: "sm" }}>
          <Text fw={600}>Total general</Text>
          <Text fw={700} size="xl">
            {formatMoney(budget.total, budget.currency)}
          </Text>
        </Group>
        <PricesNote budget={budget} />
      </Stack>

      {/* Only for those who may freeze the budget: a button that fails is
          worse than none. */}
      {canManage && (
        <SaveVersionModal
          opened={saving}
          onClose={() => setSaving(false)}
          onSaved={() => setSaving(false)}
        />
      )}
    </Stack>
  );
}

/** ADR-005 section 5: the prices are live, so the budget moves when the
 * catalogue does. Saying how old the oldest one is keeps the number honest —
 * and matters more here than on the cómputo, because this is the figure that
 * ends up in front of a client. */
function PricesNote({ budget }: { budget: BudgetOut }) {
  if (!budget.prices_as_of) return null;

  return (
    <Text size="xs" c="dimmed">
      Precios de referencia al{" "}
      {dayjs(budget.prices_as_of).format("DD/MM/YYYY")}. Es una estimación: no
      incluye costos indirectos, gastos generales, beneficio ni IVA.
    </Text>
  );
}

/** Without lines there is nothing to price. An empty table with its headings
 * and a total of cero reads as something failing to load. */
function EmptyBudget({ takeoffPath }: { takeoffPath: string }) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay nada que presupuestar</Text>
        <Text size="sm" c="dimmed" ta="center">
          El presupuesto se arma con las recetas del cómputo. Cargá las primeras
          y aparece acá, agrupado en materiales, mano de obra y equipos.
        </Text>
        <Button mt="sm" component={Link} to={takeoffPath}>
          Ir al cómputo
        </Button>
      </Stack>
    </Card>
  );
}
