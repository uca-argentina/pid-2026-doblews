import { useState } from "react";
import {
  Alert,
  Anchor,
  Button,
  Card,
  Center,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { LoadVersionModal } from "../features/budget-versions/LoadVersionModal";
import { VersionsList } from "../features/budget-versions/VersionsList";
import type { BudgetVersionSummary } from "../features/budget-versions/types";
import { useBudgetVersions } from "../features/budget-versions/useBudgetVersions";
import { useBudgetAccess } from "../features/budget/useBudgetAccess";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";

/** HU-12: every budget this work has saved, newest first.
 *
 * Reading them asks exactly what reading the cost asks — no permission of its
 * own — so useBudgetAccess is reused rather than copied. Loading one back is
 * the write, and that is the permission checked per row. */
export function ProjectBudgetVersionsPage() {
  const { firm } = useCurrentFirm();
  const { project, can } = useCurrentProject();
  const canView = useBudgetAccess();

  if (!canView) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver los costos.
      </Alert>
    );
  }

  return (
    <VersionsView
      firmId={firm.id}
      projectId={project.id}
      canManage={can("project.budget.manage")}
    />
  );
}

function VersionsView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: versions, isLoading, isError } = useBudgetVersions(
    firmId,
    projectId,
  );
  const [loading, setLoading] = useState<BudgetVersionSummary | null>(null);

  const budgetPath = `/firms/${firmId}/projects/${projectId}/budget`;

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !versions) {
    return (
      <Alert color="red" variant="light">
        No pudimos cargar las versiones. Probá de nuevo en un momento.
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <div>
        <Anchor component={Link} to={budgetPath} size="sm" c="dimmed">
          ← Presupuesto
        </Anchor>
      </div>

      <PageHeader
        title="Versiones del presupuesto"
        description="Cada una guarda los números de un momento. Una versión guardada no cambia nunca, aunque después cambien los precios o el cómputo."
        order={4}
      />

      {versions.length === 0 ? (
        <EmptyVersions budgetPath={budgetPath} canManage={canManage} />
      ) : (
        <VersionsList
          versions={versions}
          hrefFor={(versionId) => `${budgetPath}/versions/${versionId}`}
          renderActions={
            canManage
              ? (version) => (
                  <Button
                    variant="default"
                    size="compact-sm"
                    onClick={() => setLoading(version)}
                  >
                    Cargar
                  </Button>
                )
              : undefined
          }
        />
      )}

      {/* Outside the branch above on purpose: loading a version changes the
          take-off, not this list, but the confirmation should not be torn down
          while it is closing. */}
      {canManage && (
        <LoadVersionModal
          version={loading}
          onClose={() => setLoading(null)}
          onLoaded={() => setLoading(null)}
        />
      )}
    </Stack>
  );
}

/** A work whose budget was never saved. The call to action is the budget
 * screen, because that is where the button lives. */
function EmptyVersions({
  budgetPath,
  canManage,
}: {
  budgetPath: string;
  canManage: boolean;
}) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no guardaste ninguna versión</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Cuando el presupuesto esté como querés presentarlo, guardalo: queda fijo y podés seguir editando el cómputo sin tocarlo."
            : "Vas a ver acá las versiones que se guarden del presupuesto de esta obra."}
        </Text>
        {canManage && (
          <Button mt="sm" component={Link} to={budgetPath}>
            Ir al presupuesto
          </Button>
        )}
      </Stack>
    </Card>
  );
}
