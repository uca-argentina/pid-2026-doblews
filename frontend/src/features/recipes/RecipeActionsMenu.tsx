import { ActionIcon, Menu } from "@mantine/core";
import type { RecipeOut } from "../catalog/types";

interface RecipeActionsMenuProps {
  recipe: RecipeOut;
  onEdit: (recipe: RecipeOut) => void;
  onDeactivate: (recipe: RecipeOut) => void;
}

/** Edit or deactivate one recipe: support's on a general one (HU-8), an owner's
 * or architect's on their firm's own (HU-9). Same shape as MaterialActionsMenu. */
export function RecipeActionsMenu({
  recipe,
  onEdit,
  onDeactivate,
}: RecipeActionsMenuProps) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${recipe.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => onEdit(recipe)}>Editar</Menu.Item>
        <Menu.Item color="red" onClick={() => onDeactivate(recipe)}>
          Dar de baja
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
