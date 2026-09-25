import type { RecipeOut, RecipeWrite } from "../catalog/types";

/** How a recipe screen writes recipes, handed to the shared modals.
 *
 * The editor and the deactivate confirmation are the same for support's
 * general recipes (HU-8) and a firm's own (HU-9); what differs is only which
 * endpoint they call and which cache they refresh. Each page builds one of
 * these from its own mutations — useAdminRecipeWriter, useFirmRecipeWriter —
 * so the modals never know which catalogue they are editing. */
export interface RecipeWriter {
  /** Creates when recipeId is null, replaces that recipe otherwise. */
  save: (payload: RecipeWrite, recipeId: number | null) => Promise<RecipeOut>;
  saving: boolean;
  /** Logical deactivation. */
  deactivate: (recipeId: number) => Promise<void>;
  deactivating: boolean;
}
