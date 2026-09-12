import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useCurrentFirm } from "../firms/firmContext";
import { apiErrorMessage } from "../../lib/apiError";
import { useRemoveMember } from "./useMembers";
import type { MemberOut } from "./types";

interface RemoveMemberModalProps {
  /** The member being removed, or null when the modal is closed. */
  member: MemberOut | null;
  onClose: () => void;
}

/** Confirmation for the roster removal, which is logical and reversible.
 *
 * It says what actually happens, because the word "baja" suggests something
 * much heavier than what the backend does: the account survives, other firms
 * are untouched, and the person's project assignments here wait for them. An
 * owner who does not know that hesitates over a button that costs nothing. */
export function RemoveMemberModal({ member, onClose }: RemoveMemberModalProps) {
  const { firm } = useCurrentFirm();
  const removeMember = useRemoveMember(firm.id);
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
        title: "Miembro dado de baja",
        message: `${member.name} ya no forma parte de ${firm.name}.`,
        color: "obra",
      });
      close();
    } catch (error) {
      // The 409 to expect: they lead an active project, and the backend says
      // to transfer that responsibility first (HU-6).
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja a esta persona."),
      );
    }
  };

  return (
    <Modal
      opened={member !== null}
      onClose={close}
      title={member ? `Dar de baja a ${member.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Deja de ver {firm.name}, pero sigue pudiendo iniciar sesión y trabajar
          en otros estudios. Sus obras de este estudio quedan guardadas: si la
          reincorporás, vuelven solas.
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
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
