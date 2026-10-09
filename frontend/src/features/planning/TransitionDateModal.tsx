import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import dayjs from "dayjs";
import { apiErrorMessage } from "../../lib/apiError";
import { ACTION_LABELS } from "./taskStatus";
import type { TaskOut } from "./types";
import { useTransitionTask } from "./usePlanning";

/** The two actions that record a date, and so pass through this modal. */
export type DatedAction = "start" | "finish";

export interface DatedTransition {
  task: TaskOut;
  action: DatedAction;
}

interface TransitionDateModalProps {
  /** The task and action being confirmed, or null while the modal is closed. */
  transition: DatedTransition | null;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

const COPY: Record<
  DatedAction,
  { title: string; label: string; help: string; done: string }
> = {
  start: {
    title: "Iniciar",
    label: "Fecha real de inicio",
    help: "El día en que la tarea empezó de verdad. Si la estás cargando con atraso, corregilo acá.",
    done: "Tarea iniciada",
  },
  finish: {
    title: "Finalizar",
    label: "Fecha real de fin",
    help: "El día en que la tarea terminó de verdad.",
    done: "Tarea finalizada",
  },
};

/** Confirms starting or finishing a task, with the day it happened.
 *
 * HU-13: the date is today by default and can be corrected. Asking here,
 * rather than recording today and fixing it afterwards, is for the common
 * case on a site: what started on Thursday gets loaded on Monday.
 *
 * The calendar is bounded by what the backend will accept — nothing after
 * today, and no end before the start — so the usual mistakes cannot be picked.
 * The backend checks both again and is the one that decides. */
export function TransitionDateModal({
  transition,
  firmId,
  projectId,
  onClose,
}: TransitionDateModalProps) {
  return (
    <Modal
      opened={transition !== null}
      onClose={onClose}
      title={
        transition
          ? `${COPY[transition.action].title} ${transition.task.name}`
          : ""
      }
      centered
    >
      {/* Keyed, so the date starts at today each time it opens. */}
      {transition && (
        <TransitionDateForm
          key={`${transition.task.id}-${transition.action}`}
          transition={transition}
          firmId={firmId}
          projectId={projectId}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

function TransitionDateForm({
  transition,
  firmId,
  projectId,
  onClose,
}: TransitionDateModalProps & { transition: DatedTransition }) {
  const { task, action } = transition;
  const copy = COPY[action];
  const transitionTask = useTransitionTask(firmId, projectId);
  // The browser's own date: the person loading this is on the site's clock.
  const today = dayjs().format("YYYY-MM-DD");
  const [onDate, setOnDate] = useState<string | null>(today);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!onDate) return;

    setSubmitError(null);
    try {
      await transitionTask.mutateAsync({
        taskId: task.id,
        payload: { action, on_date: onDate },
      });
      notifications.show({
        title: copy.done,
        message: `${task.name}: ${dayjs(onDate).format("DD/MM/YYYY")}.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect: the task is no longer in the status this action
      // needs, because someone else moved it. The backend's sentence says so.
      setSubmitError(
        apiErrorMessage(error, "No pudimos cambiar el estado de la tarea."),
      );
    }
  };

  return (
    <Stack gap="md">
      {submitError && (
        <Alert color="red" variant="light" role="alert">
          {submitError}
        </Alert>
      )}

      <DateInput
        label={copy.label}
        description={copy.help}
        valueFormat="DD/MM/YYYY"
        value={onDate}
        onChange={setOnDate}
        maxDate={today}
        minDate={
          action === "finish"
            ? (task.actual_start_date ?? undefined)
            : undefined
        }
        error={onDate ? undefined : "Elegí una fecha"}
      />

      {action === "finish" && task.actual_start_date && (
        <Text size="xs" c="dimmed">
          Empezó el {dayjs(task.actual_start_date).format("DD/MM/YYYY")}.
        </Text>
      )}

      <Group justify="flex-end" gap="sm">
        <Button
          variant="subtle"
          onClick={onClose}
          disabled={transitionTask.isPending}
        >
          Cancelar
        </Button>
        <Button
          onClick={handleConfirm}
          loading={transitionTask.isPending}
          disabled={!onDate}
        >
          {ACTION_LABELS[action]}
        </Button>
      </Group>
    </Stack>
  );
}
