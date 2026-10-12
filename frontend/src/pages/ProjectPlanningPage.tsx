import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  Center,
  Group,
  Loader,
  SegmentedControl,
  Stack,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { ActualDatesModal } from "../features/planning/ActualDatesModal";
import { GanttChart } from "../features/planning/GanttChart";
import { ProgressModal } from "../features/planning/ProgressModal";
import { RemoveTaskModal } from "../features/planning/RemoveTaskModal";
import { ReopenTaskModal } from "../features/planning/ReopenTaskModal";
import { TaskActionsMenu } from "../features/planning/TaskActionsMenu";
import { TaskCard } from "../features/planning/TaskCard";
import { TaskDetailModal } from "../features/planning/TaskDetailModal";
import { startedSuccessors } from "../features/planning/taskFields";
import { TaskFormModal } from "../features/planning/TaskFormModal";
import { TaskLinesModal } from "../features/planning/TaskLinesModal";
import { TaskStatusMenu } from "../features/planning/TaskStatusMenu";
import { TasksTable } from "../features/planning/TasksTable";
import { UnassignedCost } from "../features/planning/UnassignedCost";
import {
  ACTION_LABELS,
  STATUS_LABELS,
  recordsDate,
} from "../features/planning/taskStatus";
import {
  TransitionDateModal,
  type DatedTransition,
} from "../features/planning/TransitionDateModal";
import type { TaskAction, TaskOut } from "../features/planning/types";
import {
  usePlanning,
  useTransitionTask,
} from "../features/planning/usePlanning";
import { usePlanningAccess } from "../features/planning/usePlanningAccess";
import { useCurrentProject } from "../features/projects/projectContext";
import { formatDate } from "../features/projects/projectFields";
import { ProjectFormModal } from "../features/projects/ProjectFormModal";
import type { ProjectDetail } from "../features/projects/types";
import { apiErrorMessage } from "../lib/apiError";

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
  const { project, can } = useCurrentProject();
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
      project={project}
      canManage={canManage}
      canEditProject={can("project.edit")}
    />
  );
}

function PlanningView({
  firmId,
  project,
  canManage,
  canEditProject,
}: {
  firmId: number;
  project: ProjectDetail;
  canManage: boolean;
  /** May set the work's start date, which every planned date counts from. */
  canEditProject: boolean;
}) {
  const projectId = project.id;
  const { data: planning, isLoading, isError } = usePlanning(firmId, projectId);
  const [adding, add] = useDisclosure(false);
  // The task each modal is open for; null means that modal is closed. Kept
  // here and not inside each row, so there is one modal of each kind on the
  // screen rather than one per task.
  const [editing, setEditing] = useState<TaskOut | null>(null);
  const [removing, setRemoving] = useState<TaskOut | null>(null);
  const [fixingDates, setFixingDates] = useState<TaskOut | null>(null);
  const [recordingProgress, setRecordingProgress] = useState<TaskOut | null>(
    null,
  );
  const [assigningLines, setAssigningLines] = useState<TaskOut | null>(null);
  const [confirming, setConfirming] = useState<DatedTransition | null>(null);
  const [reopening, setReopening] = useState<TaskOut | null>(null);
  const [editingProject, setEditingProject] = useState(false);
  // The detail is kept by id and read from the planning on every render, so
  // it follows the list when a write refreshes it — and when the detail
  // itself moves on to a predecessor or a successor.
  const [detailId, setDetailId] = useState<number | null>(null);
  const detail = planning?.tasks.find((task) => task.id === detailId) ?? null;
  // Which of the two shapes of the planning is on screen: the list or the
  // Gantt (HU-15). Kept in the URL, so reloading or sharing the address keeps
  // it; anything other than "gantt" is the list.
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") === "gantt" ? "gantt" : "list";

  const transitionTask = useTransitionTask(firmId, projectId);
  // Which task and action a one-click transition is in flight for, so only
  // that row shows a spinner.
  const inFlight = transitionTask.isPending
    ? transitionTask.variables
    : undefined;

  // The single entry point of every status action, all of which come from
  // the status badge's menu. Starting and finishing record a date, so they go through the
  // confirmation that asks for it; the other four have nothing to ask and run
  // at once.
  const handleAction = async (task: TaskOut, action: TaskAction) => {
    if (recordsDate(action)) {
      setConfirming({ task, action: action as DatedTransition["action"] });
      return;
    }
    // Reopening is allowed even when successors already started (ADR-009
    // section 5), but not by accident: those go through a confirmation that
    // names them. Without any, it is one click like the rest.
    if (action === "reopen" && startedSuccessors(task).length > 0) {
      setReopening(task);
      return;
    }

    try {
      const updated = await transitionTask.mutateAsync({
        taskId: task.id,
        payload: { action },
      });
      notifications.show({
        title: `${ACTION_LABELS[action]}: ${task.name}`,
        message: `La tarea quedó ${STATUS_LABELS[updated.status].toLowerCase()}.`,
        color: "obra",
      });
    } catch (error) {
      // No form to show it next to, so the refusal is a notification. The 409
      // to expect is a status someone else already moved.
      notifications.show({
        title: "No se pudo cambiar el estado",
        message: apiErrorMessage(
          error,
          "No pudimos cambiar el estado de la tarea.",
        ),
        color: "red",
      });
    }
  };

  // What a task offers to do, the same for the table row and the card. Only
  // for those who may manage the planning: a control that fails is worse than
  // none. Two of them, on purpose — the status badge moves the task between
  // statuses, the ⋯ menu acts on the task itself.
  const renderStatus = canManage
    ? (task: TaskOut) => (
        <TaskStatusMenu
          task={task}
          pending={inFlight?.taskId === task.id}
          onAction={handleAction}
        />
      )
    : undefined;
  const renderActions = canManage
    ? (task: TaskOut) => (
        <TaskActionsMenu
          task={task}
          onEdit={setEditing}
          onFixDates={setFixingDates}
          onRecordProgress={setRecordingProgress}
          onAssignLines={setAssigningLines}
          onRemove={setRemoving}
        />
      )
    : undefined;

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Planificación"
        action={
          <Group gap="sm">
            {/* Not offered on a phone, which always gets the cards below: the
                Gantt at 375px is left for later (ADR-009 section 12). */}
            <SegmentedControl
              visibleFrom="sm"
              aria-label="Vista de la planificación"
              value={view}
              onChange={(value) =>
                setSearchParams(value === "gantt" ? { view: "gantt" } : {}, {
                  replace: true,
                })
              }
              data={[
                { value: "list", label: "Lista" },
                { value: "gantt", label: "Gantt" },
              ]}
            />
            {canManage && <Button onClick={add.open}>Nueva tarea</Button>}
          </Group>
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
          <TransitionDateModal
            transition={confirming}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setConfirming(null)}
          />
          <ActualDatesModal
            task={fixingDates}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setFixingDates(null)}
          />
          <ProgressModal
            task={recordingProgress}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setRecordingProgress(null)}
          />
          <TaskLinesModal
            task={assigningLines}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setAssigningLines(null)}
          />
          <ReopenTaskModal
            task={reopening}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setReopening(null)}
          />
        </>
      )}
      {canEditProject && (
        <ProjectFormModal
          opened={editingProject}
          project={project}
          onClose={() => setEditingProject(false)}
        />
      )}
      <TaskDetailModal
        task={detail}
        currency={planning?.currency ?? "ARS"}
        onSelect={setDetailId}
        // One modal at a time: the detail gives way to the form, which is
        // the same one the ⋯ menu opens.
        onEdit={
          canManage
            ? (task) => {
                setDetailId(null);
                setEditing(task);
              }
            : undefined
        }
        onClose={() => setDetailId(null)}
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
          <PlanningDates
            startDate={planning.project_start_date}
            endDate={planning.planned_end_date}
            canEditProject={canEditProject}
            onEditProject={() => setEditingProject(true)}
          />

          {planning.tasks.length === 0 ? (
            <EmptyPlanning canManage={canManage} onAdd={add.open} />
          ) : (
            <>
              {/* One list, two shapes. Both are rendered and one is hidden by
                  CSS, like the team: no window measurement, and nothing to
                  re-render on resize. The wide one is the table or the Gantt,
                  whichever was picked. */}
              <Box visibleFrom="sm">
                {view !== "gantt" ? (
                  <TasksTable
                    tasks={planning.tasks}
                    currency={planning.currency}
                    showsCost={planning.total_cost !== null}
                    onOpen={(task) => setDetailId(task.id)}
                    renderStatus={renderStatus}
                    renderActions={renderActions}
                  />
                ) : planning.project_start_date === null ? (
                  <UnscheduledGantt />
                ) : (
                  <GanttChart
                    tasks={planning.tasks}
                    projectStartDate={planning.project_start_date}
                    plannedEndDate={planning.planned_end_date}
                    onOpen={(task) => setDetailId(task.id)}
                  />
                )}
              </Box>
              <Stack gap="sm" hiddenFrom="sm">
                {planning.tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    currency={planning.currency}
                    onOpen={(task) => setDetailId(task.id)}
                    status={renderStatus?.(task)}
                    actions={renderActions?.(task)}
                  />
                ))}
              </Stack>
            </>
          )}

          {/* Under the empty state too: a work with a take-off and no tasks
              has all of it waiting to be planned, and that amount is the
              reason to create the first one. */}
          <UnassignedCost planning={planning} />
        </>
      )}
    </Stack>
  );
}

/** When the work starts and when it is planned to end (HU-14).
 *
 * Without a start date nothing can be planned, so this becomes the request
 * for one: with a button to the work's form for whoever may edit it, and a
 * plain notice for everyone else. The tasks are still listed below, without
 * dates — they exist and can be loaded before the work is scheduled. */
function PlanningDates({
  startDate,
  endDate,
  canEditProject,
  onEditProject,
}: {
  startDate: string | null;
  endDate: string | null;
  canEditProject: boolean;
  onEditProject: () => void;
}) {
  if (startDate === null) {
    return (
      <Alert color="yellow" variant="light" title="Falta la fecha de inicio">
        <Stack gap="sm" align="flex-start">
          <Text size="sm">
            Las fechas de las tareas se calculan desde el inicio de la obra.
            {canEditProject
              ? " Cargala para ver cuándo cae cada una y cuándo termina la obra."
              : " Cuando se cargue, vas a ver acá cuándo cae cada tarea."}
          </Text>
          {canEditProject && (
            <Button size="xs" onClick={onEditProject}>
              Cargar fecha de inicio
            </Button>
          )}
        </Stack>
      </Alert>
    );
  }

  return (
    <Group gap="xl" px={{ sm: "sm" }}>
      <div>
        <Text size="xs" c="dimmed">
          Inicio de la obra
        </Text>
        <Text fw={500}>{formatDate(startDate)}</Text>
      </div>
      <div>
        <Text size="xs" c="dimmed">
          Fin previsto
        </Text>
        <Text fw={700}>{formatDate(endDate)}</Text>
      </div>
    </Group>
  );
}

/** The Gantt of a work with no start date (HU-15). The tasks exist, but none
 * has dates, so there is nothing to place in time: an axis with empty rows
 * would read as broken. The notice above already asks for the date. */
function UnscheduledGantt() {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay nada que ubicar en el tiempo</Text>
        <Text size="sm" c="dimmed" ta="center">
          El Gantt se dibuja con las fechas previstas de las tareas, que se
          calculan desde la fecha de inicio de la obra.
        </Text>
      </Stack>
    </Card>
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
