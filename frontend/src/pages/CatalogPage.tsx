import { useState } from "react";
import { SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { RecipeBrowser } from "../features/catalog/RecipeBrowser";
import { ResourceBrowser } from "../features/catalog/ResourceBrowser";

type View = "recipes" | "resources";

/** HU-4: the system catalogue, read-only.
 *
 * Recipes come first because they are what a work computes; the materials
 * view answers the follow-up question of what each one costs. No actions on
 * either: adding a recipe to a work is HU-5, and happens inside the work,
 * where RecipeBrowser is mounted again with an "Agregar" button. */
export function CatalogPage() {
  const [view, setView] = useState<View>("recipes");

  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Catálogo</Title>
        <Text c="dimmed" size="sm">
          Las recetas con las que se computan las obras y los materiales que
          llevan.
        </Text>
      </div>

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

      {view === "recipes" ? <RecipeBrowser /> : <ResourceBrowser />}
    </Stack>
  );
}
