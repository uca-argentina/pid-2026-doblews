import { useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { useCurrentFirm } from "../firms/firmContext";
import { useDeactivateSupplier } from "./useSuppliers";
import type { SupplierOut } from "./types";

interface DeactivateSupplierModalProps {
  /** The supplier being given up, or null when the modal is closed. */
  supplier: SupplierOut | null;
  onClose: () => void;
  /** Called after it is done, e.g. to leave the supplier's own screen. */
  onDone?: () => void;
}

/** Confirmation for giving a supplier up, which is logical.
 *
 * It says what actually happens, because "dar de baja" sounds heavier than it
 * is: the supplier leaves the comparisons of HU-18 with its whole list, and
 * nothing is erased. It also says what does not change: the budget of every
 * work keeps computing with the reference price. */
export function DeactivateSupplierModal({
  supplier,
  onClose,
  onDone,
}: DeactivateSupplierModalProps) {
  const { firm } = useCurrentFirm();
  const deactivate = useDeactivateSupplier(firm.id);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const close = () => {
    setSubmitError(null);
    onClose();
  };

  const handleDeactivate = async () => {
    if (!supplier) return;

    setSubmitError(null);
    try {
      await deactivate.mutateAsync(supplier.id);
      notifications.show({
        title: "Proveedor dado de baja",
        message: `${supplier.name} ya no aparece en las comparaciones.`,
        color: "obra",
      });
      close();
      onDone?.();
    } catch (error) {
      setSubmitError(
        apiErrorMessage(error, "No pudimos dar de baja al proveedor."),
      );
    }
  };

  return (
    <Modal
      opened={supplier !== null}
      onClose={close}
      title={supplier ? `Dar de baja a ${supplier.name}` : ""}
      centered
    >
      <Stack gap="md">
        {submitError && (
          <Alert color="red" variant="light" role="alert">
            {submitError}
          </Alert>
        )}

        <Text size="sm">
          Deja de ofrecerse y sale de las comparaciones de compra, junto con su
          lista de precios. No se borra nada, y los presupuestos de las obras no
          cambian: siguen usando el precio de referencia.
        </Text>

        <Group justify="flex-end" gap="sm">
          <Button
            variant="subtle"
            onClick={close}
            disabled={deactivate.isPending}
          >
            Cancelar
          </Button>
          <Button
            color="red"
            onClick={handleDeactivate}
            loading={deactivate.isPending}
          >
            Dar de baja
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
