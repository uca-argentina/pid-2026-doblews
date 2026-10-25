import { useState } from "react";
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import {
  AddLineModal,
  DiscardOrderModal,
  LineQuantityModal,
  LineSupplierModal,
} from "../features/purchase-orders/DraftModals";
import { OrderLinesView } from "../features/purchase-orders/OrderLinesView";
import {
  STATUS_COLORS,
  STATUS_LABELS,
  orderNumber,
} from "../features/purchase-orders/orderDisplay";
import type { PurchaseOrderLineOut } from "../features/purchase-orders/types";
import {
  useDeactivateLine,
  useOrder,
} from "../features/purchase-orders/usePurchaseOrders";
import { apiErrorMessage } from "../lib/apiError";
import { formatMoney } from "../lib/format";

/** One purchase order (HU-20): its supplier, its work and its lines, at the
 * prices they froze when the draft was generated.
 *
 * Under the firm and not under the work, like the backend's route: the
 * permissions are firm-scope, so an architect who is not on the work's team
 * opens and edits it too (ADR-011 section 6).
 *
 * While it is a draft, and for whoever holds purchase_order.manage, each line
 * can change its quantity or its supplier, or leave; materials can be added;
 * and the draft can be discarded. Issuing and cancelling are HU-21's. */
export function PurchaseOrderPage() {
  const { firm, can } = useCurrentFirm();
  const navigate = useNavigate();
  const orderId = Number(useParams().orderId);
  const { data: order, isLoading, isError } = useOrder(firm.id, orderId);
  const removeLine = useDeactivateLine(firm.id, orderId);

  const [quantityTarget, setQuantityTarget] =
    useState<PurchaseOrderLineOut | null>(null);
  const [supplierTarget, setSupplierTarget] =
    useState<PurchaseOrderLineOut | null>(null);
  const [addOpened, addModal] = useDisclosure(false);
  const [discardOpened, discardModal] = useDisclosure(false);

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !order) {
    return (
      <Alert color="red" variant="light" title="No encontramos esta orden">
        Puede que se haya descartado o que no sea de este estudio.
      </Alert>
    );
  }

  const comprasPath = `/firms/${firm.id}/projects/${order.project.id}/purchasing`;
  const editable = order.status === "draft" && can("purchase_order.manage");

  const remove = async (line: PurchaseOrderLineOut) => {
    try {
      await removeLine.mutateAsync(line.id);
      notifications.show({
        title: "Material quitado",
        message: `${line.resource.name} salió de ${orderNumber(order.number)}.`,
        color: "obra",
      });
    } catch (error) {
      notifications.show({
        title: "No pudimos quitar el material",
        message: apiErrorMessage(error, "Probá de nuevo en un momento."),
        color: "red",
      });
    }
  };

  return (
    <Stack gap="md">
      <Anchor component={Link} to={comprasPath} size="sm">
        ← Compras de {order.project.name}
      </Anchor>

      <PageHeader
        title={`${orderNumber(order.number)} · ${order.supplier.name}`}
        description={`Obra: ${order.project.name}. Los precios son los que tenía el proveedor al generar la orden.`}
        action={
          editable ? (
            <Group gap="sm">
              <Button variant="default" onClick={addModal.open}>
                Agregar material
              </Button>
              <Button variant="subtle" color="red" onClick={discardModal.open}>
                Descartar borrador
              </Button>
            </Group>
          ) : undefined
        }
      />

      <Group gap="md" align="baseline" wrap="wrap">
        <Badge color={STATUS_COLORS[order.status]} variant="light">
          {STATUS_LABELS[order.status]}
        </Badge>
        <Text fw={700} size="lg">
          Total estimado: {formatMoney(order.estimated_total, order.currency)}
        </Text>
      </Group>

      {order.lines.length === 0 ? (
        <Text size="sm" c="dimmed" ta="center" py="md">
          Este borrador no tiene materiales.
          {editable && " Agregá alguno, o descartalo si ya no hace falta."}
        </Text>
      ) : (
        <OrderLinesView
          lines={order.lines}
          currency={order.currency}
          actions={
            editable
              ? {
                  onQuantity: setQuantityTarget,
                  onSupplier: setSupplierTarget,
                  onRemove: remove,
                }
              : undefined
          }
        />
      )}

      {editable && (
        <>
          <LineQuantityModal
            firmId={firm.id}
            order={order}
            line={quantityTarget}
            onClose={() => setQuantityTarget(null)}
          />
          <LineSupplierModal
            firmId={firm.id}
            order={order}
            line={supplierTarget}
            onClose={() => setSupplierTarget(null)}
          />
          <AddLineModal
            firmId={firm.id}
            order={order}
            opened={addOpened}
            onClose={addModal.close}
          />
          <DiscardOrderModal
            firmId={firm.id}
            order={order}
            opened={discardOpened}
            onClose={discardModal.close}
            onDiscarded={() => navigate(comprasPath)}
          />
        </>
      )}
    </Stack>
  );
}
