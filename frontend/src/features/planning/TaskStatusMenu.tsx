import { Badge, Loader, Menu, Text } from "@mantine/core";
import { joinTaskNames, unfinishedPredecessors } from "./taskFields";
import {
  ACTION_LABELS,
  ACTIONS_BY_STATUS,
  STATUS_COLORS,
  STATUS_LABELS,
} from "./taskStatus";
import type { TaskAction, TaskOut } from "./types";

interface TaskStatusMenuProps {
  task: TaskOut;
  /** Whether an action on this task is being sent: the badge shows a spinner
   * and stops answering, so a second click cannot race the first. */
  pending: boolean;
  onAction: (task: TaskOut, action: TaskAction) => void;
}

/** A task's status, as the control that changes it.
 *
 * Every transition lives here and nowhere else: the badge that says what
 * status the task is in is the thing to click to move it out of it. That keeps
 * the six actions in one place, reached the same way, instead of a button for
 * the likely one and a menu for the rest — and it keeps every row the same
 * width whatever its status.
 *
 * Which actions are offered comes from ACTIONS_BY_STATUS: only the ones the
 * task's status allows, so the screen does not offer a click that would come
 * back as a 409.
 *
 * Rendered only for those who may manage the planning; everyone else gets the
 * plain TaskStatusBadge, which is the same badge without the arrow. */
export function TaskStatusMenu({
  task,
  pending,
  onAction,
}: TaskStatusMenuProps) {
  return (
    <Menu position="bottom-start" withinPortal disabled={pending}>
      <Menu.Target>
        <Badge
          component="button"
          type="button"
          variant="light"
          color={STATUS_COLORS[task.status]}
          // A Badge is a pill by default, which suits a label. This one is
          // pressed, so it takes the corner every button has (theme.ts).
          radius="var(--mantine-radius-default)"
          rightSection={
            pending ? (
              <Loader size={10} color={STATUS_COLORS[task.status]} />
            ) : (
              "▾"
            )
          }
          style={{ cursor: pending ? "default" : "pointer" }}
          aria-label={`Estado de ${task.name}: ${STATUS_LABELS[task.status]}. Cambiar`}
        >
          {STATUS_LABELS[task.status]}
        </Badge>
      </Menu.Target>
      <Menu.Dropdown>
        {ACTIONS_BY_STATUS[task.status].map((action) => {
          // HU-14: a task cannot start while a predecessor is unfinished.
          // Offered disabled, saying what it waits for, rather than hidden:
          // an "Iniciar" that vanished would read as a bug.
          const waitingFor =
            action === "start" ? unfinishedPredecessors(task) : [];
          return (
            <Menu.Item
              key={action}
              disabled={waitingFor.length > 0}
              onClick={() => onAction(task, action)}
            >
              {ACTION_LABELS[action]}
              {waitingFor.length > 0 && (
                <Text size="xs" c="dimmed" maw={240}>
                  Falta que {waitingFor.length === 1 ? "finalice" : "finalicen"}{" "}
                  {joinTaskNames(waitingFor)}.
                </Text>
              )}
            </Menu.Item>
          );
        })}
      </Menu.Dropdown>
    </Menu>
  );
}
