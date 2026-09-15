import { ActionIcon, Menu } from "@mantine/core";
import type { RecipeOut } from "./types";

interface RecipeAdminActionsMenuProps {
  recipe: RecipeOut;
  onEdit: (recipe: RecipeOut) => void;
  onDeactivate: (recipe: RecipeOut) => void;
}

/** What support can do to one recipe, same shape as MaterialActionsMenu. */
export function RecipeAdminActionsMenu({
  recipe,
  onEdit,
  onDeactivate,
}: RecipeAdminActionsMenuProps) {
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
