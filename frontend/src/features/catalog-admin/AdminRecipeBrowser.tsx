import { useMemo, useState, type ReactNode } from "react";
import { Alert, Center, Loader, Stack, Text, TextInput } from "@mantine/core";
import { matchesSearch } from "../../lib/format";
import { RecipeCard } from "../catalog/RecipeCard";
import type { RecipeOut } from "./types";
import { useAdminRecipes } from "./useCatalogAdmin";

interface AdminRecipeBrowserProps {
  /** What each card offers to do with its recipe. Same render-prop contract
   * as HU-4/HU-5's RecipeBrowser (renderAction), kept for consistency even
   * though this component has one caller today. */
  renderAction?: (recipe: RecipeOut) => ReactNode;
}

/** Search and list the catalogue's recipes for support to administer (HU-8).
 *
 * Deliberately not RecipeBrowser (HU-4/HU-5's firm-scoped one): this needs
 * its own data source, the platform-scoped admin endpoint. RecipeCard itself
 * is presentation-only and firm-agnostic, so it is reused as is. */
export function AdminRecipeBrowser({ renderAction }: AdminRecipeBrowserProps) {
  const { data: recipes, isLoading, isError } = useAdminRecipes();
  const [query, setQuery] = useState("");

  const visible = useMemo(
    () => recipes?.filter((recipe) => matchesSearch(recipe.name, query)) ?? [],
    [recipes, query],
  );

  return (
    <Stack gap="sm">
      <TextInput
        placeholder="Buscar receta por nombre"
        aria-label="Buscar receta"
        value={query}
        onChange={(event) => setQuery(event.currentTarget.value)}
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar las recetas. Probá de nuevo en un momento.
        </Alert>
      )}

      {recipes && visible.length === 0 && (
        <Text size="sm" c="dimmed" ta="center" py="md">
          {recipes.length === 0
            ? "El catálogo todavía no tiene recetas."
            : "Ninguna receta coincide con la búsqueda."}
        </Text>
      )}

      {visible.map((recipe) => (
        <RecipeCard
          key={recipe.id}
          recipe={recipe}
          action={renderAction?.(recipe)}
          // Support only ever sees general recipes here (ADR-006), so a
          // "General" badge on every card would say nothing.
          showOrigin={false}
        />
      ))}
    </Stack>
  );
}
