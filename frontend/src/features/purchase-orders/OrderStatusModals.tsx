import { type FormEvent, useState } from "react";
import { Alert, Button, Group, Modal, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { apiErrorMessage } from "../../lib/apiError";
import { formatDay, orderNumber } from "./orderDisplay";
import type { PurchaseOrderSummary, ReceiptOut } from "./types";
import {
  useCancelOrder,
  useDeactivateReceipt,
  useIssueOrder,
} from "./usePurchaseOrders";

/** The moves of an order that are confirmed before they happen, because none
 * of them is undone: issuing a draft, cancelling an order, and letting go of
 * the last delivery registered (HU-22). */

interface StatusModalProps {
  firmId: number;
  order: PurchaseOrderSummary;
  opened: boolean;
  onClose: () => void;
}

function ConfirmModal({
  title,
  explanation,
  submitLabel,
  color,
  pending,
  opened,
  onClose,
  onConfirm,
  failure,
}: {
  title: string;
  explanation: string;
  submitLabel: string;
  color?: string;
  pending: boolean;
  opened: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  failure: string;
}) {
  const [error, setError] = useState<string | null>(null);
  // The modal stays mounted between openings: a failure from the last one
  // should not greet the next.
  const close = () => {
    setError(null);
    onClose();
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      await onConfirm();
      close();
    } catch (caught) {
      setError(apiErrorMessage(caught, failure));
    }
  };

  return (
    <Modal opened={opened} onClose={close} title={title} centered>
      <form onSubmit={submit} noValidate>
        <Stack gap="md">
          {error && (
            <Alert color="red" variant="light" role="alert">
              {error}
            </Alert>
          )}
          <Text size="sm">{explanation}</Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={close} disabled={pending}>
              Volver
            </Button>
            <Button type="submit" loading={pending} color={color}>
              {submitLabel}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function IssueOrderModal({
  firmId,
  order,
  opened,
  onClose,
}: StatusModalProps) {
  const issue = useIssueOrder(firmId);
  return (
    <ConfirmModal
      title={`Emitir ${orderNumber(order.number)}`}
      explanation={`La orden queda emitida a ${order.supplier.name} y ya no se puede editar: si algo cambia, se anula y se genera otra.`}
      submitLabel="Emitir"
      pending={issue.isPending}
      opened={opened}
      onClose={onClose}
      failure="No pudimos emitir la orden."
      onConfirm={async () => {
        await issue.mutateAsync(order.id);
        notifications.show({
          title: "Orden emitida",
          message: `${orderNumber(order.number)} quedó emitida a ${order.supplier.name}.`,
          color: "obra",
        });
      }}
    />
  );
}

export function CancelOrderModal({
  firmId,
  order,
  opened,
  onClose,
}: StatusModalProps) {
  const cancel = useCancelOrder(firmId);
  return (
    <ConfirmModal
      title={`Anular ${orderNumber(order.number)}`}
      explanation="La anulación es definitiva: la orden queda en el historial como anulada y sus cantidades vuelven a quedar sin pedir, para generarlas de nuevo desde Compras."
      submitLabel="Anular"
      color="red"
      pending={cancel.isPending}
      opened={opened}
      onClose={onClose}
      failure="No pudimos anular la orden."
      onConfirm={async () => {
        await cancel.mutateAsync(order.id);
        notifications.show({
          title: "Orden anulada",
          message: `${orderNumber(order.number)} quedó anulada.`,
          color: "obra",
        });
      }}
    />
  );
}

export function CancelReceiptModal({
  firmId,
  order,
  receipt,
  opened,
  onClose,
}: StatusModalProps & { receipt: ReceiptOut }) {
  const drop = useDeactivateReceipt(firmId, order.id);
  return (
    <ConfirmModal
      title="Anular la última recepción"
      explanation={`La entrega del ${formatDay(receipt.received_on)} deja de contar: sus cantidades vuelven a quedar pendientes y el costo real de la orden se recalcula. Se puede volver a cargar.`}
      submitLabel="Anular recepción"
      color="red"
      pending={drop.isPending}
      opened={opened}
      onClose={onClose}
      failure="No pudimos anular la recepción."
      onConfirm={async () => {
        await drop.mutateAsync(receipt.id);
        notifications.show({
          title: "Recepción anulada",
          message: `La entrega del ${formatDay(receipt.received_on)} salió de ${orderNumber(order.number)}.`,
          color: "obra",
        });
      }}
    />
  );
}
