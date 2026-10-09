import { ActionIcon, Menu } from "@mantine/core";
import type { TaskOut } from "./types";

interface TaskActionsMenuProps {
  task: TaskOut;
  onEdit: (task: TaskOut) => void;
  onFixDates: (task: TaskOut) => void;
  onRemove: (task: TaskOut) => void;
}

/** The ⋯ menu of one task: what can be done to the task itself, the same
 * shape as a take-off line's.
 *
 * Changing its status is not here. That is TaskStatusMenu, on the status
 * badge, so the transitions are all in one place.
 *
 * Rendered only for those who may manage the planning: the page decides that
 * once and does not pass actions otherwise, so this has no permission to ask. */
export function TaskActionsMenu({
  task,
  onEdit,
  onFixDates,
  onRemove,
}: TaskActionsMenuProps) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${task.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => onEdit(task)}>Editar</Menu.Item>
        {/* A pending task has no actual dates to correct. */}
        {task.status !== "pending" && (
          <Menu.Item onClick={() => onFixDates(task)}>
            Corregir fechas
          </Menu.Item>
        )}
        <Menu.Item color="red" onClick={() => onRemove(task)}>
          Dar de baja
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
