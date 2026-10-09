import { Alert, Box, Card, Center, Loader, Stack, Text } from "@mantine/core";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { PlanningTotals } from "../features/planning/PlanningTotals";
import { TaskCard } from "../features/planning/TaskCard";
import { TasksTable } from "../features/planning/TasksTable";
import { usePlanning } from "../features/planning/usePlanning";
import { usePlanningAccess } from "../features/planning/usePlanningAccess";
import { useCurrentProject } from "../features/projects/projectContext";

/** HU-13: the tasks a work is split into, who answers for each, and what each
 * costs.
 *
 * A sibling of the work's data under ProjectLayout, which has already resolved
 * the work and the caller's permissions on it: this fetches only the planning.
 *
 * Split in two like the take-off screen, so the read only happens for someone
 * who may do it. */
export function ProjectPlanningPage() {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const { canView, canManage } = usePlanningAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL. The
    // backend would refuse the read anyway.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver la planificación.
      </Alert>
    );
  }

  return (
    <PlanningView
      firmId={firm.id}
      projectId={project.id}
      canManage={canManage}
    />
  );
}

function PlanningView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: planning, isLoading, isError } = usePlanning(firmId, projectId);

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Planificación"
        description="Las tareas de la obra: quién hace cada una, cuánto lleva y en qué estado está."
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar la planificación. Probá de nuevo en un momento.
        </Alert>
      )}

      {planning && (
        <>
          {planning.tasks.length === 0 ? (
            <EmptyPlanning canManage={canManage} />
          ) : (
            <>
              {/* One list, two shapes. Both are rendered and one is hidden by
                  CSS, like the team: no window measurement, and nothing to
                  re-render on resize. */}
              <Box visibleFrom="sm">
                <TasksTable
                  tasks={planning.tasks}
                  currency={planning.currency}
                  showsCost={planning.total_cost !== null}
                />
              </Box>
              <Stack gap="sm" hiddenFrom="sm">
                {planning.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    currency={planning.currency}
                  />
                ))}
              </Stack>
            </>
          )}

          {/* Under the empty state too: a work with a take-off and no tasks
              has all of it waiting to be planned, and that amount is the
              reason to create the first one. */}
          <PlanningTotals planning={planning} />
        </>
      )}
    </Stack>
  );
}

/** A planning with no tasks. An empty table with its headings would read as
 * something failing to load (same as the take-off). */
function EmptyPlanning({ canManage }: { canManage: boolean }) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay tareas en esta obra</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Dividí la obra en tareas, poneles responsable y duración, y asignales las líneas del cómputo que le corresponden a cada una."
            : "Vas a ver acá las tareas de la obra cuando se cargue su planificación."}
        </Text>
      </Stack>
    </Card>
  );
}
