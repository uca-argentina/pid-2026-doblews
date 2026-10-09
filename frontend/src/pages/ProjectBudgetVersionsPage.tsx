import { useState } from "react";
import {
  Alert,
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

/** HU-12: every budget this work has saved, newest first. It is what the
 * "Presupuestos" tab opens on: the live budget is on the take-off, and this is
 * what was frozen from it.
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
  const {
    data: versions,
    isLoading,
    isError,
  } = useBudgetVersions(firmId, projectId);
  const [loading, setLoading] = useState<BudgetVersionSummary | null>(null);

  const projectPath = `/firms/${firmId}/projects/${projectId}`;
  const takeoffPath = `${projectPath}/takeoff`;

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
      <PageHeader title="Presupuestos guardados" order={4} />

      {versions.length === 0 ? (
        <EmptyVersions takeoffPath={takeoffPath} canManage={canManage} />
      ) : (
        <VersionsList
          versions={versions}
          hrefFor={(versionId) => `${projectPath}/budget/versions/${versionId}`}
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

/** A work whose budget was never saved. The call to action is the take-off,
 * because that is where the button lives. */
function EmptyVersions({
  takeoffPath,
  canManage,
}: {
  takeoffPath: string;
  canManage: boolean;
}) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay presupuestos guardados</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Cuando el cómputo esté como querés presentarlo, guardá una versión desde ahí: queda fija y podés seguir editándolo sin tocarla."
            : "Vas a ver acá los presupuestos que se guarden de esta obra."}
        </Text>
        {canManage && (
          <Button mt="sm" component={Link} to={takeoffPath}>
            Ir al cómputo
          </Button>
        )}
      </Stack>
    </Card>
  );
}
