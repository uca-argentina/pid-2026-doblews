import {
  Alert,
  Anchor,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { SaveVersionModal } from "../features/budget-versions/SaveVersionModal";
import { useBudgetVersions } from "../features/budget-versions/useBudgetVersions";
import type { BudgetVersionSummary } from "../features/budget-versions/types";
import { BudgetGroupSection } from "../features/budget/BudgetGroupSection";
import { BudgetTotal } from "../features/budget/BudgetTotal";
import { toSectionGroups } from "../features/budget/types";
import { useBudget } from "../features/budget/useBudget";
import { useBudgetAccess } from "../features/budget/useBudgetAccess";
import { useCurrentFirm } from "../features/firms/firmContext";
import { usePlanningAccess } from "../features/planning/usePlanningAccess";
import { useCurrentProject } from "../features/projects/projectContext";
import { AddLineModal } from "../features/takeoff/AddLineModal";
import { AssignLineTaskModal } from "../features/takeoff/AssignLineTaskModal";
import { EditLineModal } from "../features/takeoff/EditLineModal";
import { LineActionsMenu } from "../features/takeoff/LineActionsMenu";
import { RemoveLineModal } from "../features/takeoff/RemoveLineModal";
import { TakeoffLines } from "../features/takeoff/TakeoffLines";
import { TakeoffMaterials } from "../features/takeoff/TakeoffMaterials";
import type { TakeoffLineOut } from "../features/takeoff/types";
import { useTakeoff } from "../features/takeoff/useTakeoff";
import { useTakeoffAccess } from "../features/takeoff/useTakeoffAccess";

/** The live numbers of a work, all of them and nowhere else: the recipes loaded
 * onto it (HU-5), what they add up to in resources and money (HU-11), and the
 * button that freezes that as a saved budget (HU-12).
 *
 * One screen because they are one thing — the budget is the take-off priced —
 * and showing them on two tabs meant the same table and the same total twice.
 * What a saved budget looked like on its day lives under "Presupuestos".
 *
 * A sibling of the work's data under ProjectLayout, which has already resolved
 * the work and the caller's permissions on it.
 *
 * The total opens the screen because it is the answer the architect came for.
 * The recipes follow because they are what gets edited, and the breakdown by
 * resource closes it: it is the longest part and the one consulted least. */
export function ProjectTakeoffPage() {
  const { firm } = useCurrentFirm();
  const { project, can } = useCurrentProject();
  const { canView, canManage } = useTakeoffAccess();
  // Costs are the budget's rule, not the take-off's: the project client reads
  // this screen and sees quantities only (HU-10).
  const canSeeCosts = useBudgetAccess();
  // Where a line is planned answers to the planning's permission, not the
  // take-off's (HU-13). The same roles hold both today.
  const { canManage: canAssignTasks } = usePlanningAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL. The
    // backend would refuse the read anyway.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver el cómputo.
      </Alert>
    );
  }

  return (
    <TakeoffView
      firmId={firm.id}
      projectId={project.id}
      canManage={canManage}
      canAssignTasks={canAssignTasks}
      canSeeCosts={canSeeCosts}
      canSaveVersion={can("project.budget.manage")}
    />
  );
}

function TakeoffView({
  firmId,
  projectId,
  canManage,
  canAssignTasks,
  canSeeCosts,
  canSaveVersion,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
  canAssignTasks: boolean;
  canSeeCosts: boolean;
  canSaveVersion: boolean;
}) {
  const { data: takeoff, isLoading, isError } = useTakeoff(firmId, projectId);
  // Asked only on behalf of whoever may see costs: the endpoint refuses the
  // rest. Both hang below the work's key, so editing a line refetches the two
  // together and the total never trails the recipes above it.
  const budget = useBudget(firmId, projectId, canSeeCosts);
  // Only to say which saved budget this take-off is, if any. Not waited for
  // and not reported when it fails: it is one line under the total.
  const versions = useBudgetVersions(firmId, projectId, canSeeCosts);
  const [adding, add] = useDisclosure(false);
  const [saving, save] = useDisclosure(false);
  // The line each modal is open for; null means that modal is closed.
  const [editing, setEditing] = useState<TakeoffLineOut | null>(null);
  const [removing, setRemoving] = useState<TakeoffLineOut | null>(null);
  const [assigning, setAssigning] = useState<TakeoffLineOut | null>(null);

  if (isLoading || budget.isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !takeoff) {
    return (
      <Alert color="red" variant="light">
        No pudimos cargar el cómputo. Probá de nuevo en un momento.
      </Alert>
    );
  }

  // Empty groups are left out, as on a saved budget: a work with no equipment
  // shows no "Equipos" heading over nothing.
  const groups = budget.data
    ? toSectionGroups(budget.data.groups).filter(
        (group) => group.items.length > 0,
      )
    : [];
  const versionsPath = `/firms/${firmId}/projects/${projectId}/budget`;

  return (
    <>
      {takeoff.lines.length === 0 ? (
        <EmptyTakeoff canManage={canManage} onAdd={add.open} />
      ) : (
        <Stack gap="xl">
          <Stack gap="md">
            <PageHeader
              title="Cómputo de la obra"
              order={4}
              action={
                // Not the filled button: "Agregar receta" below is what this
                // screen is used for most, and two filled buttons compete.
                canSaveVersion ? (
                  <Button variant="default" onClick={save.open}>
                    Guardar versión
                  </Button>
                ) : undefined
              }
            />

            {budget.data && <BudgetTotal budget={budget.data} />}
            {budget.isError && (
              // The recipes below still work without the prices, so this
              // replaces the total rather than the whole screen.
              <Alert color="red" variant="light">
                No pudimos cargar los costos. Probá de nuevo en un momento.
              </Alert>
            )}

            {canSeeCosts && (
              <Group gap="xs">
                <Anchor component={Link} to={versionsPath} size="sm">
                  Ver presupuestos guardados
                </Anchor>
                {versions.data && versions.data.length > 0 && (
                  <Text size="sm" c="dimmed">
                    · {savedAs(versions.data)}
                  </Text>
                )}
              </Group>
            )}
          </Stack>

          <Stack gap="sm">
            <Group justify="space-between" align="center" wrap="wrap" gap="sm">
              <Title order={4}>Recetas cargadas</Title>
              {canManage && <Button onClick={add.open}>Agregar receta</Button>}
            </Group>
            <TakeoffLines
              lines={takeoff.lines}
              renderActions={
                canManage || canAssignTasks
                  ? (line) => (
                      <LineActionsMenu
                        line={line}
                        onEdit={canManage ? setEditing : undefined}
                        onRemove={canManage ? setRemoving : undefined}
                        onAssignTask={canAssignTasks ? setAssigning : undefined}
                      />
                    )
                  : undefined
              }
            />
          </Stack>

          {budget.data ? (
            groups.map((group) => (
              <BudgetGroupSection
                key={group.type}
                group={group}
                currency={budget.data.currency}
              />
            ))
          ) : (
            <Stack gap="sm">
              {/* Not "Materiales": since T-06 the recipes also yield hours of
                  labour and of equipment, and TakeoffMaterials groups the
                  three under their own headings. */}
              <Title order={4}>Qué necesita la obra</Title>
              <TakeoffMaterials takeoff={takeoff} />
            </Stack>
          )}
        </Stack>
      )}

      {/* Outside both branches on purpose: adding the first line flips the
          screen from empty to full while the modal is still closing, and a
          modal rendered inside either branch would be torn down mid-way — as
          would removing the last line. Only for those who may manage the
          take-off: a button that fails is worse than none. */}
      {canManage && (
        <>
          <AddLineModal
            opened={adding}
            firmId={firmId}
            projectId={projectId}
            onClose={add.close}
          />
          <EditLineModal
            line={editing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setEditing(null)}
          />
          <RemoveLineModal
            line={removing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setRemoving(null)}
          />
        </>
      )}
      {/* Only for those who may freeze the budget: a button that fails is
          worse than none. */}
      {canSaveVersion && (
        <SaveVersionModal
          opened={saving}
          onClose={save.close}
          onSaved={save.close}
        />
      )}
      {canAssignTasks && (
        <AssignLineTaskModal
          line={assigning}
          firmId={firmId}
          projectId={projectId}
          onClose={() => setAssigning(null)}
        />
      )}
    </>
  );
}

/** How the take-off of today relates to the budgets saved from it. The
 * backend decides which versions match; this only words it. */
function savedAs(versions: BudgetVersionSummary[]): string {
  const matching = versions
    .filter((version) => version.matches_takeoff)
    .map((version) => `v${version.version_number}`);

  if (matching.length === 0) return "Tiene cambios sin guardar";
  // Newest first, as the listing: saving twice in a row gives two.
  const names = new Intl.ListFormat("es", { type: "conjunction" }).format(
    matching,
  );
  return `Igual a ${matching.length > 1 ? "las" : "la"} ${names}`;
}

/** A take-off with no lines has no materials either. An empty table with its
 * headings would read as something failing to load (same as ProjectsPage). */
function EmptyTakeoff({
  canManage,
  onAdd,
}: {
  canManage: boolean;
  onAdd: () => void;
}) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay recetas en el cómputo</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Elegí una receta del catálogo y cargá cuánto lleva la obra: el cómputo suma sus materiales solo."
            : "Vas a ver acá los materiales de la obra cuando se carguen sus recetas."}
        </Text>
        {canManage && (
          <Button mt="sm" onClick={onAdd}>
            Agregar la primera receta
          </Button>
        )}
      </Stack>
    </Card>
  );
}
