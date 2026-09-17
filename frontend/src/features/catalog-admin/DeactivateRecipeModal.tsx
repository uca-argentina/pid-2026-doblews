import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useDeactivateRecipe } from "./useCatalogAdmin";
import type { RecipeOut } from "./types";

interface DeactivateRecipeModalProps {
  /** The recipe being deactivated, or null when the modal is closed. */
  recipe: RecipeOut | null;
  onClose: () => void;
}

/** Confirmation for deactivating a recipe. Same shape as
 * DeactivateResourceModal, but with no 409-in-use case to design for:
 * ADR-005 section 6 carries no usage guard on a recipe's deactivation — the
 * works that already added it keep computing from its live rows, so the only
 * error path here is the generic fallback (an unknown/already-inactive id,
 * a network failure). */
export function DeactivateRecipeModal({
  recipe,
  onClose,
}: DeactivateRecipeModalProps) {
  const deactivateRecipe = useDeactivateRecipe();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (!recipe) return;

    setSubmitError(null);
    try {
      await deactivateRecipe.mutateAsync(recipe.id);
      notifications.show({
        title: "Receta dada de baja",
        message: `${recipe.name} ya no aparece en el catálogo.`,
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja la receta."),
      );
    }
  };

  return (
    <Modal
      opened={recipe !== null}
      onClose={close}
      title={recipe ? `Dar de baja ${recipe.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Esto saca a {recipe?.name} del catálogo. Las obras que ya la agregaron
          a su cómputo siguen calculando con ella; solo deja de poder elegirse
          en cómputos nuevos.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={deactivateRecipe.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleConfirm}
            loading={deactivateRecipe.isPending}
          >
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
