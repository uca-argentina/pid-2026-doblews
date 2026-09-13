import { useMemo, useState, type ReactNode } from "react";
import { Alert, Center, Loader, Stack, Text, TextInput } from "@mantine/core";
import { matchesSearch } from "../../lib/format";
import { useCurrentFirm } from "../firms/firmContext";
import { RecipeCard } from "./RecipeCard";
import type { RecipeOut } from "./types";
import { useRecipes } from "./useCatalog";

interface RecipeBrowserProps {
  /** What each card offers to do with its recipe. Omitted in HU-4's catalogue,
   * where the recipes are only read; HU-5 passes an "Agregar" button. */
  renderAction?: (recipe: RecipeOut) => ReactNode;
}

/** Search the catalogue's recipes and look inside them.
 *
 * Built to be mounted in two places: the catalogue page (HU-4) and the
 * "Agregar al cómputo" modal of a work (HU-5). That is why it fetches its own
 * data and handles its own loading and error states instead of receiving a
 * list — the modal only has to render it — and why the one thing that differs
 * between the two, the action, comes in as a render prop.
 *
 * The filter runs here and not on the server: the whole catalogue is already
 * in the cache, and it is a handful of rows (HU-4, out of scope). It matches
 * the name only, which is what HU-4 asks for. */
export function RecipeBrowser({ renderAction }: RecipeBrowserProps) {
  const { firm } = useCurrentFirm();
  const { data: recipes, isLoading, isError } = useRecipes(firm.id);
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
        />
      ))}
    </Stack>
  );
}
