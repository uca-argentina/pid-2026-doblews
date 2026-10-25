import { useMemo, useState } from "react";
import {
  Alert,
  Anchor,
  Center,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { OrdersList } from "../features/purchase-orders/OrdersList";
import { STATUS_LABELS } from "../features/purchase-orders/orderDisplay";
import type {
  NamedRef,
  OrderStatus,
  PurchaseOrderSummary,
} from "../features/purchase-orders/types";
import { useFirmOrders } from "../features/purchase-orders/usePurchaseOrders";

/** HU-21: every purchase order of the firm, newest first, filterable by work,
 * supplier and state.
 *
 * Behind purchase_order.view, like its route. The filters run on the client:
 * a firm's orders are few, and the options come from the orders themselves,
 * so a filter never offers a work or a supplier with nothing to show. */
export function PurchaseOrdersPage() {
  const { firm } = useCurrentFirm();
  const { data: orders, isLoading, isError } = useFirmOrders(firm.id);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [supplierId, setSupplierId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const projects = useMemo(
    () => options(orders ?? [], (order) => order.project),
    [orders],
  );
  const suppliers = useMemo(
    () => options(orders ?? [], (order) => order.supplier),
    [orders],
  );
  const statuses = useMemo(
    () =>
      (Object.keys(STATUS_LABELS) as OrderStatus[])
        .filter((value) => orders?.some((order) => order.status === value))
        .map((value) => ({ value, label: STATUS_LABELS[value] })),
    [orders],
  );

  const shown = (orders ?? []).filter(
    (order) =>
      (!projectId || String(order.project.id) === projectId) &&
      (!supplierId || String(order.supplier.id) === supplierId) &&
      (!status || order.status === status),
  );

  return (
    <Stack gap="md">
      <PageHeader
        title="Órdenes de compra"
        description="Todas las órdenes del estudio, de todas las obras. Se generan desde Compras de cada obra."
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar las órdenes. Probá de nuevo en un momento.
        </Alert>
      )}

      {orders && orders.length === 0 && (
        <Stack align="center" gap="xs" py="xl">
          <Text fw={600}>Todavía no hay órdenes de compra</Text>
          <Text size="sm" c="dimmed" ta="center" maw={420}>
            Las órdenes se generan desde Compras de cada obra: elegís los
            materiales y se arma un borrador por proveedor.
          </Text>
          <Anchor component={Link} to={`/firms/${firm.id}/projects`} size="sm">
            Ir a las obras →
          </Anchor>
        </Stack>
      )}

      {orders && orders.length > 0 && (
        <>
          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
            <Select
              label="Obra"
              placeholder="Todas"
              data={projects}
              value={projectId}
              onChange={setProjectId}
              clearable
              searchable
            />
            <Select
              label="Proveedor"
              placeholder="Todos"
              data={suppliers}
              value={supplierId}
              onChange={setSupplierId}
              clearable
              searchable
            />
            <Select
              label="Estado"
              placeholder="Todos"
              data={statuses}
              value={status}
              onChange={setStatus}
              clearable
            />
          </SimpleGrid>

          {shown.length === 0 ? (
            <Text size="sm" c="dimmed" ta="center" py="md">
              Ninguna orden cumple con estos filtros.
            </Text>
          ) : (
            <OrdersList firmId={firm.id} orders={shown} showProject />
          )}
        </>
      )}
    </Stack>
  );
}

/** The distinct works or suppliers of these orders, by name, as Select options. */
function options(
  orders: PurchaseOrderSummary[],
  pick: (order: PurchaseOrderSummary) => NamedRef,
): { value: string; label: string }[] {
  const byId = new Map<number, string>();
  for (const order of orders) byId.set(pick(order).id, pick(order).name);
  return [...byId]
    .map(([id, name]) => ({ value: String(id), label: name }))
    .sort((a, b) => a.label.localeCompare(b.label, "es"));
}
