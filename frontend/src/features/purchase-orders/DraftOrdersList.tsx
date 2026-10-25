import { Alert, Card, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { formatMoney } from "../../lib/format";
import { orderNumber } from "./orderDisplay";
import { useProjectOrders } from "./usePurchaseOrders";

interface DraftOrdersListProps {
  firmId: number;
  projectId: number;
}

/** The work's drafts, under its comparison (HU-20): one per supplier, each
 * leading to its own page, where it is edited.
 *
 * Only drafts for now. HU-21 turns this into the work's listing of orders in
 * every state, with issuing and cancelling. */
export function DraftOrdersList({ firmId, projectId }: DraftOrdersListProps) {
  const {
    data: orders,
    isLoading,
    isError,
  } = useProjectOrders(firmId, projectId, "draft");

  return (
    <Stack gap="sm">
      <Title order={5}>Borradores de órdenes</Title>

      {isLoading && <Loader size="sm" />}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar los borradores. Probá de nuevo en un momento.
        </Alert>
      )}

      {orders && orders.length === 0 && (
        <Text size="sm" c="dimmed">
          No hay borradores. Elegí materiales en la tabla de arriba y tocá
          "Generar órdenes": se arma uno por proveedor, con el más económico.
        </Text>
      )}

      {orders?.map((order) => (
        <Card
          key={order.id}
          withBorder
          padding="sm"
          radius="md"
          component={Link}
          to={`/firms/${firmId}/purchase-orders/${order.id}`}
        >
          <Group justify="space-between" wrap="wrap" gap="xs">
            <div>
              <Text fw={600}>
                {orderNumber(order.number)} · {order.supplier.name}
              </Text>
              <Text size="sm" c="dimmed">
                {order.line_count === 1
                  ? "1 material"
                  : `${order.line_count} materiales`}
              </Text>
            </div>
            <Text fw={700}>
              {formatMoney(order.estimated_total, order.currency)}
            </Text>
          </Group>
        </Card>
      ))}
    </Stack>
  );
}
