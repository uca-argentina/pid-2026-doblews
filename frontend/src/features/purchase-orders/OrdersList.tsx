import { Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";
import { formatMoney } from "../../lib/format";
import { formatDateTime, orderNumber } from "./orderDisplay";
import { OrderStatusBadge } from "./OrderStatusBadge";
import type { PurchaseOrderSummary } from "./types";

interface OrdersListProps {
  firmId: number;
  orders: PurchaseOrderSummary[];
  /** The work column, for the firm's listing; a work's own listing drops it. */
  showProject?: boolean;
}

/** Orders in any state, each leading to its page (HU-21): the work's, under
 * its comparison, and the firm's, with filters.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS. */
export function OrdersList({ firmId, orders, showProject }: OrdersListProps) {
  const navigate = useNavigate();
  const orderPath = (order: PurchaseOrderSummary) =>
    `/firms/${firmId}/purchase-orders/${order.id}`;

  return (
    <>
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Orden</Table.Th>
                {showProject && <Table.Th>Obra</Table.Th>}
                <Table.Th>Proveedor</Table.Th>
                <Table.Th>Estado</Table.Th>
                <Table.Th>Creada</Table.Th>
                <Table.Th ta="right">Total estimado</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {orders.map((order) => (
                <Table.Tr
                  key={order.id}
                  onClick={() => navigate(orderPath(order))}
                  style={{ cursor: "pointer" }}
                >
                  <Table.Td>
                    {/* A real link too, so the row is reachable by keyboard
                        and opens in a new tab like any link. */}
                    <Text
                      component={Link}
                      to={orderPath(order)}
                      fw={600}
                      onClick={(event) => event.stopPropagation()}
                    >
                      {orderNumber(order.number)}
                    </Text>
                  </Table.Td>
                  {showProject && <Table.Td>{order.project.name}</Table.Td>}
                  <Table.Td>{order.supplier.name}</Table.Td>
                  <Table.Td>
                    <OrderStatusBadge status={order.status} />
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{formatDateTime(order.created_at)}</Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    <Text fw={700}>
                      {formatMoney(order.estimated_total, order.currency)}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {orders.map((order) => (
          <Card
            key={order.id}
            withBorder
            padding="sm"
            radius="md"
            component={Link}
            to={orderPath(order)}
          >
            <Stack gap={4}>
              <Group justify="space-between" wrap="nowrap" gap="xs">
                <Text fw={600}>{orderNumber(order.number)}</Text>
                <OrderStatusBadge status={order.status} />
              </Group>
              <Text size="sm">{order.supplier.name}</Text>
              {showProject && (
                <Text size="sm" c="dimmed">
                  Obra: {order.project.name}
                </Text>
              )}
              <Group justify="space-between" wrap="wrap" gap="xs">
                <Text size="sm" c="dimmed">
                  {formatDateTime(order.created_at)}
                </Text>
                <Text fw={700}>
                  {formatMoney(order.estimated_total, order.currency)}
                </Text>
              </Group>
            </Stack>
          </Card>
        ))}
      </Stack>
    </>
  );
}
