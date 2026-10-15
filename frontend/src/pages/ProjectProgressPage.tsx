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
import dayjs from "dayjs";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { FixBaselineModal } from "../features/planning/FixBaselineModal";
import { isOverdue } from "../features/planning/progress";
import { ProgressCard } from "../features/planning/ProgressCard";
import { ProgressModal } from "../features/planning/ProgressModal";
import { ProgressSummary } from "../features/planning/ProgressSummary";
import { ProgressTable } from "../features/planning/ProgressTable";
import type { PlanningOut, TaskOut } from "../features/planning/types";
import { usePlanning } from "../features/planning/usePlanning";
import { usePlanningAccess } from "../features/planning/usePlanningAccess";
import { useCurrentProject } from "../features/projects/projectContext";

/** HU-16: how much of each task is done against what was planned, and of the
 * work as a whole.
 *
 * A tab of its own and not a part of the planning, which is the screen for
 * the day to day — what is done when. This one answers a different question,
 * "how are we doing?", and it is the only place where progress is recorded
 * and the planning is fixed.
 *
 * It reads the same answer as the planning (GET .../tasks), under the same
 * permissions: whoever sees the tasks sees their progress, the client
 * included. Split in two like that page, so the read only happens for
 * someone who may do it. */
export function ProjectProgressPage() {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const { canView, canManage } = usePlanningAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver el avance.
      </Alert>
    );
  }

  return (
    <ProgressView
      firmId={firm.id}
      projectId={project.id}
      canManage={canManage}
    />
  );
}

function ProgressView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: planning, isLoading, isError } = usePlanning(firmId, projectId);
  const [fixing, fix] = useDisclosure(false);
  const [recording, setRecording] = useState<TaskOut | null>(null);
  const today = dayjs().format("YYYY-MM-DD");

  // Fixing copies the planned dates, so there have to be some: a start date
  // to count from and at least one task. Until then the button is not
  // offered, and the notices below say what is missing.
  const canFix =
    canManage &&
    planning !== undefined &&
    planning.project_start_date !== null &&
    planning.tasks.length > 0;
  const fixed = planning?.baseline_set_on != null;

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Avance"
        action={
          canFix && (
            <Button variant={fixed ? "default" : "filled"} onClick={fix.open}>
              {fixed ? "Volver a fijar" : "Fijar planificación"}
            </Button>
          )
        }
      />

      {/* Outside the loading and empty branches, like the planning's: a modal
          rendered inside one would be torn down when the list refreshes. */}
      {canManage && (
        <>
          <FixBaselineModal
            opened={fixing}
            fixedOn={planning?.baseline_set_on ?? null}
            plannedEndDate={planning?.planned_end_date ?? null}
            firmId={firmId}
            projectId={projectId}
            onClose={fix.close}
          />
          <ProgressModal
            task={recording}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setRecording(null)}
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
          No pudimos cargar el avance. Probá de nuevo en un momento.
        </Alert>
      )}

      {planning &&
        (planning.tasks.length === 0 ? (
          <EmptyProgress />
        ) : (
          <>
            <Baseline planning={planning} today={today} canManage={canManage} />

            {/* One list, two shapes, one hidden by CSS: no window
                measurement, like the planning. */}
            <Box visibleFrom="sm">
              <ProgressTable
                tasks={planning.tasks}
                today={today}
                onRecord={canManage ? setRecording : undefined}
              />
            </Box>
            <Stack gap="sm" hiddenFrom="sm">
              {planning.tasks.map((task) => (
                <ProgressCard
                  key={task.id}
                  task={task}
                  today={today}
                  onRecord={canManage ? setRecording : undefined}
                />
              ))}
            </Stack>
          </>
        ))}
    </Stack>
  );
}

/** What stands above the list: the summary once a planning is fixed, and
 * until then the notice of what is missing to fix one. The list below is
 * there either way, since progress can be recorded before anything is fixed. */
function Baseline({
  planning,
  today,
  canManage,
}: {
  planning: PlanningOut;
  today: string;
  canManage: boolean;
}) {
  if (planning.baseline_set_on !== null) {
    return (
      <ProgressSummary
        planning={planning}
        overdueCount={
          planning.tasks.filter((task) => isOverdue(task, today)).length
        }
      />
    );
  }

  if (planning.project_start_date === null) {
    return (
      <Alert color="yellow" variant="light" title="Falta la fecha de inicio">
        Sin la fecha de inicio de la obra las tareas no tienen fechas previstas,
        así que no hay contra qué comparar el avance. Se carga desde
        Planificación.
      </Alert>
    );
  }

  return (
    <Alert color="blue" variant="light" title="Falta fijar la planificación">
      Las fechas previstas se corren solas con cada atraso, así que el avance se
      compara contra una copia de ellas.
      {canManage
        ? " Fijala cuando la planificación esté lista para ver cuánto debería llevar cada tarea."
        : " Cuando se fije, vas a ver acá cuánto debería llevar cada tarea."}
    </Alert>
  );
}

/** A work with no tasks. An empty table with its headings would read as
 * something failing to load. */
function EmptyProgress() {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay tareas en esta obra</Text>
        <Text size="sm" c="dimmed" ta="center">
          El avance se registra sobre las tareas de la obra, que se cargan en
          Planificación.
        </Text>
      </Stack>
    </Card>
  );
}
