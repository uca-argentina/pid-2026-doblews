import { ActionIcon, Menu } from "@mantine/core";
import type { TaskOut } from "./types";

interface TaskActionsMenuProps {
  task: TaskOut;
  onEdit: (task: TaskOut) => void;
  onRemove: (task: TaskOut) => void;
}

/** The ⋯ menu of one task, the same shape as a take-off line's.
 *
 * Rendered only for those who may manage the planning: the page decides that
 * once and does not pass actions otherwise, so this has no permission to ask. */
export function TaskActionsMenu({
  task,
  onEdit,
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
        <Menu.Item color="red" onClick={() => onRemove(task)}>
          Dar de baja
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
