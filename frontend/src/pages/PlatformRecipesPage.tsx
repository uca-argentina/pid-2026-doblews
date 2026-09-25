import { useState } from "react";
import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { AdminRecipeBrowser } from "../features/catalog-admin/AdminRecipeBrowser";
import { RecipeAdminActionsMenu } from "../features/catalog-admin/RecipeAdminActionsMenu";
import type { RecipeOut } from "../features/catalog-admin/types";
import {
  useAdminRecipeWriter,
  useAdminResources,
} from "../features/catalog-admin/useCatalogAdmin";
import { DeactivateRecipeModal } from "../features/recipes/DeactivateRecipeModal";
import { RecipeFormModal } from "../features/recipes/RecipeFormModal";

/** HU-8: every recipe of the system catalogue, administered by support. */
export function PlatformRecipesPage() {
  // null doubles as "creating", same convention as MaterialFormModal's
  // resource prop / ProjectFormModal's project prop.
  const [editTarget, setEditTarget] = useState<RecipeOut | null>(null);
  const [formOpened, formModal] = useDisclosure(false);
  // Which recipe the deactivate modal is about, and null when it is closed —
  // one shared modal at page level, same pattern as FirmStatusModal.
  const [deactivateTarget, setDeactivateTarget] = useState<RecipeOut | null>(
    null,
  );
  const writer = useAdminRecipeWriter();
  const resources = useAdminResources();

  const openCreate = () => {
    setEditTarget(null);
    formModal.open();
  };
  const openEdit = (recipe: RecipeOut) => {
    setEditTarget(recipe);
    formModal.open();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <div>
          <Title order={3}>Recetas</Title>
          <Text c="dimmed" size="sm">
            Las recetas del catálogo del sistema, con lo que lleva cada una.
          </Text>
        </div>
        <Button onClick={openCreate}>Nueva receta</Button>
      </Group>

      <RecipeFormModal
        opened={formOpened}
        recipe={editTarget}
        onClose={formModal.close}
        resources={resources.data}
        writer={writer}
      />
      <DeactivateRecipeModal
        recipe={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
        writer={writer}
      />

      <AdminRecipeBrowser
        renderAction={(recipe) => (
          <RecipeAdminActionsMenu
            recipe={recipe}
            onEdit={openEdit}
            onDeactivate={setDeactivateTarget}
          />
        )}
      />
    </Stack>
  );
}
