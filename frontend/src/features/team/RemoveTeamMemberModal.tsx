import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";
import { useRemoveTeamMember } from "./useTeam";
import type { ProjectMemberOut } from "./types";

interface RemoveTeamMemberModalProps {
  /** The member being taken off, or null when the modal is closed. */
  member: ProjectMemberOut | null;
  onClose: () => void;
}

/** Confirmation for taking someone off a work.
 *
 * It says what actually happens, because this removal is not like the roster's:
 * there the person is deactivated and their assignments wait for them, here the
 * assignment is really deleted (project_member has no state to flip). They keep
 * their account and their place in the studio, and they can be put back on the
 * work at any time — but their seat, and the date they joined it, are gone. */
export function RemoveTeamMemberModal({
  member,
  onClose,
}: RemoveTeamMemberModalProps) {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const removeMember = useRemoveTeamMember(firm.id, project.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleRemove = async () => {
    if (!member) return;

    setSubmitError(null);
    try {
      await removeMember.mutateAsync(member.account_id);
      notifications.show({
        title: "Miembro quitado del equipo",
        message: `${member.name} ya no participa de ${project.name}.`,
        color: "obra",
      });
      close();
    } catch (error) {
      // The 409 to expect: they are the lead, and the work cannot be left
      // without one. The backend says to transfer the role first.
      setSubmitError(
        apiErrorMessage(error, "No pudimos quitar a esta persona del equipo."),
      );
    }
  };

  return (
    <Modal
      opened={member !== null}
      onClose={close}
      title={member ? `Quitar a ${member.name} del equipo` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Deja de ver esta obra de inmediato, en cuanto haga cualquier cosa en
          la aplicación. Sigue siendo parte de {firm.name} y de las demás obras
          en las que participe, y podés volver a sumarlo cuando quieras.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={removeMember.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleRemove}
            loading={removeMember.isPending}
          >
            Quitar del equipo
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
