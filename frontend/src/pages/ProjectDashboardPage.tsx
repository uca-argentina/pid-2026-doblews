import { Alert, Center, Loader, SimpleGrid, Stack } from "@mantine/core";
import { PageHeader } from "../components/PageHeader";
import { BudgetBlock } from "../features/dashboard/BudgetBlock";
import { ProgressBlock } from "../features/dashboard/ProgressBlock";
import { ProjectionBlock } from "../features/dashboard/ProjectionBlock";
import { useDashboard } from "../features/dashboard/useDashboard";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";

/** HU-19: a work at a glance — how the money is going and how the progress
 * is going, so a deviation shows without walking every tab.
 *
 * Read only. Each block says what it is missing and links to the tab that
 * loads it; nothing is edited here.
 *
 * About money, so it opens to whoever may see costs (D-16): project.cost.view
 * on the work, or project.view_all for the owner. The client of the work does
 * not see the tab, and gets this notice if they type the URL. */
export function ProjectDashboardPage() {
  const firm = useCurrentFirm();
  const { project, can } = useCurrentProject();

  if (!can("project.cost.view") && !firm.can("project.view_all")) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver el dashboard.
      </Alert>
    );
  }

  return <DashboardView firmId={firm.firm.id} projectId={project.id} />;
}

function DashboardView({
  firmId,
  projectId,
}: {
  firmId: number;
  projectId: number;
}) {
  const {
    data: dashboard,
    isLoading,
    isError,
  } = useDashboard(firmId, projectId);
  const base = `/firms/${firmId}/projects/${projectId}`;

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Dashboard"
        description="Cómo viene la plata y cómo viene el avance de la obra."
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar el dashboard. Probá de nuevo en un momento.
        </Alert>
      )}

      {dashboard && (
        <>
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            <BudgetBlock
              budget={dashboard.budget}
              currency={dashboard.currency}
              versionsPath={`${base}/budget`}
            />
            <ProgressBlock
              block={dashboard.progress}
              planningPath={`${base}/planning`}
              progressPath={`${base}/progress`}
            />
          </SimpleGrid>
          <ProjectionBlock
            projection={dashboard.projection}
            currency={dashboard.currency}
            planningPath={`${base}/planning`}
          />
        </>
      )}
    </Stack>
  );
}
