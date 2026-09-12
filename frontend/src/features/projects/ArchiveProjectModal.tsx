import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import { apiErrorMessage } from "../../lib/apiError";
import { useArchiveProject } from "./useProjects";
import type { ProjectOut } from "./types";

interface ArchiveProjectModalProps {
  opened: boolean;
  project: ProjectOut;
  onClose: () => void;
  /** Where to go once the work is gone. It cannot be this screen: its own
   * detail answers 404 from the moment it is archived. */
  onArchived: () => void;
}

/** Confirmation for archiving a work, which is a logical removal.
 *
 * It says what actually happens, because "dar de baja" suggests something much
 * heavier than what the backend does: the row stays, the team stays assigned,
 * and nothing about the work is lost. What changes is that it leaves the
 * listing and its own screen stops answering.
 *
 * What it does not promise is undoing it, because no story has built that yet:
 * there is no screen that lists archived works and no endpoint that restores
 * one. Saying "podés recuperarla" would be a lie today, so it says the shape
 * of the truth instead. */
export function ArchiveProjectModal({
  opened,
  project,
  onClose,
  onArchived,
}: ArchiveProjectModalProps) {
  const { firm } = useCurrentFirm();
  const archiveProject = useArchiveProject(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleArchive = async () => {
    setSubmitError(null);
    try {
      await archiveProject.mutateAsync(project.id);
      notifications.show({
        title: "Obra dada de baja",
        message: `${project.name} ya no aparece en el listado.`,
        color: "obra",
      });
      onArchived();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos dar de baja la obra."));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title={`Dar de baja ${project.name}`}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Sale del listado de obras de {firm.name} y deja de poder abrirse. No
          se borra nada: sus datos y su equipo quedan guardados tal como están.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={archiveProject.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleArchive}
            loading={archiveProject.isPending}
          >
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
