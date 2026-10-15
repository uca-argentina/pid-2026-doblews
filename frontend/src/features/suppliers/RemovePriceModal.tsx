import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import { useRemovePrice } from "./useSuppliers";
import type { SupplierPriceOut } from "./types";

interface RemovePriceModalProps {
  supplierId: number;
  /** The row being removed, or null when the modal is closed. */
  price: SupplierPriceOut | null;
  onClose: () => void;
}

/** Confirmation for taking a material out of a supplier's list. Logical: the
 * row is kept, and loading the same material again later starts a new one. */
export function RemovePriceModal({
  supplierId,
  price,
  onClose,
}: RemovePriceModalProps) {
  const { firm } = useCurrentFirm();
  const remove = useRemovePrice(firm.id, supplierId);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleRemove = async () => {
    if (!price) return;

    setSubmitError(null);
    try {
      await remove.mutateAsync(price.id);
      notifications.show({
        title: "Material quitado",
        message: `${price.resource.name} ya no está en la lista.`,
        color: "obra",
      });
      close();
    } catch (error) {
      setSubmitError(apiErrorMessage(error, "No pudimos quitar el material."));
    }
  };

  return (
    <Modal
      opened={price !== null}
      onClose={close}
      title={price ? `Quitar ${price.resource.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Este proveedor deja de aparecer en las comparaciones de este material.
          Podés volver a cargarlo cuando quieras.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button variant="subtle" onClick={close} disabled={remove.isPending}>
            Cancelar
          </Button>
          <Button color="red" onClick={handleRemove} loading={remove.isPending}>
            Quitar
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
