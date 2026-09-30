import { useState } from "react";
import { Button, SegmentedControl, Stack } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { PageHeader } from "../components/PageHeader";
import { RecipeBrowser } from "../features/catalog/RecipeBrowser";
import { ResourceBrowser } from "../features/catalog/ResourceBrowser";
import type { RecipeOut } from "../features/catalog/types";
import {
  useFirmRecipeWriter,
  useResources,
} from "../features/catalog/useCatalog";
import { useCurrentFirm } from "../features/firms/firmContext";
import { DeactivateRecipeModal } from "../features/recipes/DeactivateRecipeModal";
import { RecipeActionsMenu } from "../features/recipes/RecipeActionsMenu";
import { RecipeFormModal } from "../features/recipes/RecipeFormModal";

type View = "recipes" | "resources";

/** HU-4's catalogue, plus the firm's own recipes (HU-9).
 *
 * Recipes come first because they are what a work computes; the materials
 * view answers the follow-up question of what each one costs. The recipes mix
 * the general ones and the firm's own, each badged with its origin.
 *
 * Writing is offered only to whoever holds recipe.manage (owner, architect),
 * and only on the firm's own recipes: the general ones never show edit or
 * deactivate, since support maintains them (HU-8). A client sees the same
 * list with no actions. The backend refuses both cases again on its own. */
export function CatalogPage() {
  const { firm, can } = useCurrentFirm();
  const [view, setView] = useState<View>("recipes");
  const canManage = can("recipe.manage");

  // null doubles as "creating", same convention as PlatformRecipesPage.
  const [editTarget, setEditTarget] = useState<RecipeOut | null>(null);
  const [formOpened, formModal] = useDisclosure(false);
  const [deactivateTarget, setDeactivateTarget] = useState<RecipeOut | null>(
    null,
  );
  const writer = useFirmRecipeWriter(firm.id);
  // The same cached list the materials view reads, so opening the editor
  // after browsing materials costs no request.
  const resources = useResources(firm.id);

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
      <PageHeader
        title="Catálogo"
        description="Las recetas con las que se computan las obras y los materiales que llevan."
        action={
          canManage && view === "recipes" ? (
            <Button onClick={openCreate}>Nueva receta</Button>
          ) : undefined
        }
      />

      <SegmentedControl
        value={view}
        onChange={(value) => setView(value as View)}
        data={[
          { value: "recipes", label: "Recetas" },
          { value: "resources", label: "Materiales" },
        ]}
        // Full width on a phone so both options are an easy tap; its natural
        // width beside the content on anything wider.
        fullWidth
        maw={{ sm: 320 }}
      />

      {canManage && (
        <>
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
        </>
      )}

      {view === "recipes" ? (
        <RecipeBrowser
          renderAction={(recipe) =>
            canManage && recipe.origin === "firm" ? (
              <RecipeActionsMenu
                recipe={recipe}
                onEdit={openEdit}
                onDeactivate={setDeactivateTarget}
              />
            ) : null
          }
        />
      ) : (
        <ResourceBrowser />
      )}
    </Stack>
  );
}
