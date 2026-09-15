import { ActionIcon, Menu } from "@mantine/core";
import type { RecipeOut } from "./types";

interface RecipeAdminActionsMenuProps {
  recipe: RecipeOut;
  onEdit: (recipe: RecipeOut) => void;
}

/** What support can do to one recipe, same shape as MaterialActionsMenu.
 *
 * "Dar de baja" joins this menu once DeactivateRecipeModal exists. */
export function RecipeAdminActionsMenu({
  recipe,
  onEdit,
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
      </Menu.Dropdown>
    </Menu>
  );
}
