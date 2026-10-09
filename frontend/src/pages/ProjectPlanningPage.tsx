import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { PlanningTotals } from "../features/planning/PlanningTotals";
import { RemoveTaskModal } from "../features/planning/RemoveTaskModal";
import { TaskActionsMenu } from "../features/planning/TaskActionsMenu";
import { TaskCard } from "../features/planning/TaskCard";
import { TaskFormModal } from "../features/planning/TaskFormModal";
import { TasksTable } from "../features/planning/TasksTable";
import type { TaskOut } from "../features/planning/types";
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
  const [adding, add] = useDisclosure(false);
  // The task each modal is open for; null means that modal is closed. Kept
  // here and not inside each row, so there is one modal of each kind on the
  // screen rather than one per task.
  const [editing, setEditing] = useState<TaskOut | null>(null);
  const [removing, setRemoving] = useState<TaskOut | null>(null);

  // What a task offers to do, the same for the table row and the card. Only
  // for those who may manage the planning: a button that fails is worse than
  // none.
  const renderActions = canManage
    ? (task: TaskOut) => (
        <TaskActionsMenu
          task={task}
          onEdit={setEditing}
          onRemove={setRemoving}
        />
      )
    : undefined;

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Planificación"
        description="Las tareas de la obra: quién hace cada una, cuánto lleva y en qué estado está."
        action={
          canManage ? (
            <Button onClick={add.open}>Nueva tarea</Button>
          ) : undefined
        }
      />

      {/* Outside the loading and empty branches on purpose, as in the
          take-off: creating the first task flips the screen from empty to
          full while the modal is still closing, and a modal rendered inside
          either branch would be torn down mid-way. One form modal serves both
          creating and editing. */}
      {canManage && (
        <>
          <TaskFormModal
            opened={adding || editing !== null}
            task={editing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => {
              add.close();
              setEditing(null);
            }}
          />
          <RemoveTaskModal
            task={removing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setRemoving(null)}
          />
        </>
      )}

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
            <EmptyPlanning canManage={canManage} onAdd={add.open} />
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
                  renderActions={renderActions}
                />
              </Box>
              <Stack gap="sm" hiddenFrom="sm">
                {planning.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    currency={planning.currency}
                    actions={renderActions?.(task)}
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
function EmptyPlanning({
  canManage,
  onAdd,
}: {
  canManage: boolean;
  onAdd: () => void;
}) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay tareas en esta obra</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Dividí la obra en tareas, poneles responsable y duración, y asignales las líneas del cómputo que le corresponden a cada una."
            : "Vas a ver acá las tareas de la obra cuando se cargue su planificación."}
        </Text>
        {canManage && (
          <Button mt="sm" onClick={onAdd}>
            Crear la primera tarea
          </Button>
        )}
      </Stack>
    </Card>
  );
}
