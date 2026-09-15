import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useDeactivateResource } from "./useCatalogAdmin";
import type { ResourceOut } from "./types";

interface DeactivateResourceModalProps {
  /** The material being deactivated, or null when the modal is closed. */
  resource: ResourceOut | null;
  onClose: () => void;
}

/** Confirmation for deactivating a material.
 *
 * One direction only, unlike FirmStatusModal: HU-8 has no reincorporation
 * screen — a deactivated name is simply free to load again (the model's own
 * uq_resource_name_active index already anticipates that).
 *
 * The interesting case is the 409 the backend answers when an active recipe
 * still uses this material: its detail names every one of them
 * ("Este material se usa en estas recetas activas: X, Y..."), written to be
 * shown as is, so nothing here adds copy for that case — apiErrorMessage
 * already passes a 409's string detail through untouched. */
export function DeactivateResourceModal({
  resource,
  onClose,
}: DeactivateResourceModalProps) {
  const deactivateResource = useDeactivateResource();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (!resource) return;

    setSubmitError(null);
    try {
      await deactivateResource.mutateAsync(resource.id);
      notifications.show({
        title: "Material dado de baja",
        message: `${resource.name} ya no aparece en el catálogo.`,
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja el material."),
      );
    }
  };

  return (
    <Modal
      opened={resource !== null}
      onClose={close}
      title={resource ? `Dar de baja ${resource.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Esto saca a {resource?.name} del catálogo. Las obras que ya lo usan no
          se ven afectadas, pero no vas a poder elegirlo en recetas nuevas.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={deactivateResource.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleConfirm}
            loading={deactivateResource.isPending}
          >
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
