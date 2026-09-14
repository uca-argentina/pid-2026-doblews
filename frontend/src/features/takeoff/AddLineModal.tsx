import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Stack,
  Text,
  useMantineTheme,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMediaQuery } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { RecipeBrowser } from "../catalog/RecipeBrowser";
import type { RecipeOut } from "../catalog/types";
import { LineFields } from "./LineFields";
import {
  emptyLine,
  linePayload,
  lineValidation,
  type LineValues,
} from "./lineForm";
import { useCreateLine } from "./useTakeoff";

interface AddLineModalProps {
  opened: boolean;
  firmId: number;
  projectId: number;
  onClose: () => void;
}

/** HU-5's add: choose a recipe from the catalogue, then say how much of it.
 *
 * Two steps in one modal. The first is HU-4's RecipeBrowser, mounted with the
 * "Agregar" action it was built to receive, so a recipe can be searched and
 * unfolded before choosing. The second asks for the quantity in that recipe's
 * unit. What is added to a work is always a recipe, never a loose material
 * (ADR-003 section 1).
 *
 * Full screen on a phone, where HU-5 asks the whole add to be doable: a
 * centered modal there leaves a search box, a list of cards and a keyboard
 * fighting over a third of the screen. */
export function AddLineModal({
  opened,
  firmId,
  projectId,
  onClose,
}: AddLineModalProps) {
  const theme = useMantineTheme();
  const isPhone = useMediaQuery(`(max-width: ${theme.breakpoints.sm})`);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Agregar al cómputo"
      fullScreen={isPhone}
      size="lg"
      centered
    >
      {/* Mounted per opening, so every add starts back at the recipe list
          with an empty form, as ProjectFormModal does. */}
      {opened && (
        <AddLineSteps firmId={firmId} projectId={projectId} onClose={onClose} />
      )}
    </Modal>
  );
}

function AddLineSteps({
  firmId,
  projectId,
  onClose,
}: Omit<AddLineModalProps, "opened">) {
  const [recipe, setRecipe] = useState<RecipeOut | null>(null);

  if (!recipe) {
    return (
      <RecipeBrowser
        renderAction={(candidate) => (
          <Button size="compact-sm" onClick={() => setRecipe(candidate)}>
            Agregar
          </Button>
        )}
      />
    );
  }

  return (
    <LineForm
      firmId={firmId}
      projectId={projectId}
      recipe={recipe}
      onBack={() => setRecipe(null)}
      onClose={onClose}
    />
  );
}

function LineForm({
  firmId,
  projectId,
  recipe,
  onBack,
  onClose,
}: {
  firmId: number;
  projectId: number;
  recipe: RecipeOut;
  onBack: () => void;
  onClose: () => void;
}) {
  const createLine = useCreateLine(firmId, projectId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const form = useForm<LineValues>({
    initialValues: emptyLine,
    validate: lineValidation,
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitError(null);
    try {
      await createLine.mutateAsync({
        recipe_id: recipe.id,
        ...linePayload(values),
      });
      notifications.show({
        title: "Receta agregada",
        message: `${recipe.name} ya suma al cómputo.`,
        color: "obra",
      });
      onClose();
    } catch (error) {
      // The 409 to expect is a recipe retired while this was open; its text
      // is the backend's and tells the architect to pick another.
      setSubmitError(apiErrorMessage(error, "No pudimos agregar la receta."));
    }
  });

  return (
    <form onSubmit={handleSubmit} noValidate>
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <div>
          <Group justify="space-between" align="flex-start" wrap="nowrap">
            <Text fw={600}>{recipe.name}</Text>
            <Badge variant="light" style={{ flexShrink: 0 }}>
              por {recipe.unit.abbreviation}
            </Badge>
          </Group>
          <Button
            variant="subtle"
            size="compact-sm"
            px={0}
            onClick={onBack}
            disabled={createLine.isPending}
          >
            ← Cambiar receta
          </Button>
        </div>

        <LineFields form={form} unit={recipe.unit.abbreviation} />

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={onClose}
            disabled={createLine.isPending}
          >
            Cancelar
          </Button>
          <Button type="submit" loading={createLine.isPending}>
            Agregar
          </Button>
        </Group>
      </Stack>
    </form>
  );
}
