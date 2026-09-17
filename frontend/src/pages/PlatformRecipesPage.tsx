import { useState } from "react";
import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { AdminRecipeBrowser } from "../features/catalog-admin/AdminRecipeBrowser";
import { DeactivateRecipeModal } from "../features/catalog-admin/DeactivateRecipeModal";
import { RecipeAdminActionsMenu } from "../features/catalog-admin/RecipeAdminActionsMenu";
import { RecipeFormModal } from "../features/catalog-admin/RecipeFormModal";
import type { RecipeOut } from "../features/catalog-admin/types";

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
      />
      <DeactivateRecipeModal
        recipe={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
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
