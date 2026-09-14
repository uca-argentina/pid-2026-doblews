import { ActionIcon, Menu } from "@mantine/core";
import type { TakeoffLineOut } from "./types";

interface LineActionsMenuProps {
  line: TakeoffLineOut;
  onEdit: (line: TakeoffLineOut) => void;
  onRemove: (line: TakeoffLineOut) => void;
}

/** The ⋯ menu of one take-off line, the same shape as the roster's.
 *
 * Rendered only for those who may manage the take-off: the page decides that
 * once and does not pass actions otherwise, so this has no permission to ask. */
export function LineActionsMenu({
  line,
  onEdit,
  onRemove,
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
        <Menu.Item onClick={() => onEdit(line)}>Editar</Menu.Item>
        <Menu.Item color="red" onClick={() => onRemove(line)}>
          Dar de baja
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
