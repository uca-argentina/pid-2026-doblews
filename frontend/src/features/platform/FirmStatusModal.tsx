import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useChangeFirmStatus } from "./usePlatform";
import type { FirmAdminOut } from "./types";

interface FirmStatusModalProps {
  /** The firm whose state is changing, or null when the modal is closed. The
   * direction comes from it: an active firm is being suspended, a suspended
   * one reactivated. */
  firm: FirmAdminOut | null;
  onClose: () => void;
}

/** Confirmation for suspending or reactivating a firm.
 *
 * Suspending locks every member out on their next request, so it is confirmed.
 * The text says both halves of what happens, as RemoveMemberModal does: the
 * consequence is immediate and wide, and nothing is lost, so reactivating
 * brings everything back. Reactivating is confirmed too, for symmetry and
 * because it reopens a firm someone may have closed on purpose. */
export function FirmStatusModal({ firm, onClose }: FirmStatusModalProps) {
  const changeStatus = useChangeFirmStatus();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const suspending = firm?.is_active ?? false;

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (!firm) return;

    setSubmitError(null);
    try {
      await changeStatus.mutateAsync({
        firmId: firm.id,
        isActive: !suspending,
      });
      notifications.show({
        title: suspending ? "Estudio suspendido" : "Estudio reactivado",
        message: suspending
          ? `Los miembros de ${firm.name} ya no pueden entrar.`
          : `Los miembros de ${firm.name} pueden volver a entrar.`,
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(
          error,
          suspending
            ? "No pudimos suspender el estudio."
            : "No pudimos reactivar el estudio.",
        ),
      );
    }
  };

  return (
    <Modal
      opened={firm !== null}
      onClose={close}
      title={
        firm ? `${suspending ? "Suspender" : "Reactivar"} ${firm.name}` : ""
      }
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          {suspending
            ? "Sus miembros dejan de poder entrar al estudio desde ahora, aunque sigan con la sesión abierta. No se borra nada: sus obras, cómputos y padrón quedan guardados, y al reactivarlo vuelven como estaban."
            : "Sus miembros vuelven a poder entrar, y encuentran sus obras, cómputos y padrón como estaban al suspenderlo."}
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={changeStatus.isPending}
          >
            Cancelar
          </Button>
          <Button
            color={suspending ? "red" : undefined}
            onClick={handleConfirm}
            loading={changeStatus.isPending}
          >
            {suspending ? "Suspender" : "Reactivar"}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
