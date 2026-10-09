import { ActionIcon, Menu } from "@mantine/core";
import type { TakeoffLineOut } from "./types";

interface LineActionsMenuProps {
  line: TakeoffLineOut;
  /** Editing and removing the line, for those who may manage the take-off.
   * Left out for anyone else, and then neither is offered. */
  onEdit?: (line: TakeoffLineOut) => void;
  onRemove?: (line: TakeoffLineOut) => void;
  /** Assigning the line to a task, for those who may manage the planning
   * (HU-13). Left out for anyone else. */
  onAssignTask?: (line: TakeoffLineOut) => void;
}

/** The ⋯ menu of one take-off line, the same shape as the roster's.
 *
 * It asks no permission itself: the page decides what the caller may do and
 * passes only those handlers, so an option that is not passed is not shown.
 * The two kinds of action answer to two permissions — project.recipe.manage
 * for the line, project.task.manage for where it is planned — which today the
 * same roles hold, and which this keeps apart for the day they do not. */
export function LineActionsMenu({
  line,
  onEdit,
  onRemove,
  onAssignTask,
}: LineActionsMenuProps) {
  const label = line.note
    ? `${line.recipe.name} (${line.note})`
    : line.recipe.name;

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${label}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {onEdit && <Menu.Item onClick={() => onEdit(line)}>Editar</Menu.Item>}
        {onAssignTask && (
          <Menu.Item onClick={() => onAssignTask(line)}>
            Asignar a tarea
          </Menu.Item>
        )}
        {onRemove && (
          <Menu.Item color="red" onClick={() => onRemove(line)}>
            Dar de baja
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  );
}
