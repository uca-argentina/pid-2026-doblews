import {
  ActionIcon,
  Box,
  Card,
  Group,
  Menu,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { formatMoney, formatQuantity } from "../../lib/format";
import { differenceTone } from "./orderDisplay";
import type { PurchaseOrderLineOut } from "./types";

interface OrderLinesViewProps {
  lines: PurchaseOrderLineOut[];
  currency: string;
  /** True once the order was issued, when what matters per line is what has
   * arrived of it rather than the price it was agreed at (HU-22). */
  deliveries?: boolean;
  /** Present only while the order is a draft and the caller may manage it. */
  actions?: {
    onQuantity: (line: PurchaseOrderLineOut) => void;
    onSupplier: (line: PurchaseOrderLineOut) => void;
    onRemove: (line: PurchaseOrderLineOut) => void;
  };
}

/** An order's lines, at the price each froze when it was made (ADR-011
 * section 2). A table from sm up and cards below it, both rendered and one
 * hidden by CSS.
 *
 * Two shapes of the same table. While the order is a draft it shows what is
 * being agreed: quantity, price, shipping, estimated total. Once it is issued
 * it shows what is happening: ordered, received, pending, and the two costs of
 * what arrived. Nine columns at once would need a scrollbar on a laptop to say
 * less, and the order's header already carries both totals. */
export function OrderLinesView({
  lines,
  currency,
  deliveries = false,
  actions,
}: OrderLinesViewProps) {
  if (deliveries) {
    return <DeliveryLines lines={lines} currency={currency} />;
  }
  return (
    <>
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={680}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Material</Table.Th>
                <Table.Th ta="right">Cantidad</Table.Th>
                <Table.Th ta="right">Precio</Table.Th>
                <Table.Th ta="right">Envío</Table.Th>
                <Table.Th ta="right">Total estimado</Table.Th>
                {actions && <Table.Th w={60} />}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {lines.map((line) => (
                <Table.Tr key={line.id}>
                  <Table.Td>
                    <Text fw={500}>{line.resource.name}</Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatQuantity(line.quantity)} {line.unit.abbreviation}
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatMoney(line.unit_price, currency)} por{" "}
                    {line.unit.abbreviation}
                  </Table.Td>
                  <Table.Td ta="right">{shippingText(line, currency)}</Table.Td>
                  <Table.Td ta="right">
                    <Text fw={600}>
                      {formatMoney(line.estimated_total, currency)}
                    </Text>
                  </Table.Td>
                  {actions && (
                    <Table.Td>
                      <LineMenu line={line} actions={actions} />
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {lines.map((line) => (
          <Card key={line.id} withBorder padding="sm" radius="md">
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Stack gap={2}>
                <Text fw={600}>{line.resource.name}</Text>
                <Text size="sm" c="dimmed">
                  {formatQuantity(line.quantity)} {line.unit.abbreviation} ×{" "}
                  {formatMoney(line.unit_price, currency)} · Envío:{" "}
                  {shippingText(line, currency)}
                </Text>
                <Text fw={700}>
                  {formatMoney(line.estimated_total, currency)}
                </Text>
              </Stack>
              {actions && <LineMenu line={line} actions={actions} />}
            </Group>
          </Card>
        ))}
      </Stack>
    </>
  );
}

function LineMenu({
  line,
  actions,
}: {
  line: PurchaseOrderLineOut;
  actions: NonNullable<OrderLinesViewProps["actions"]>;
}) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${line.resource.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => actions.onQuantity(line)}>
          Cambiar cantidad
        </Menu.Item>
        <Menu.Item onClick={() => actions.onSupplier(line)}>
          Cambiar proveedor
        </Menu.Item>
        <Menu.Item color="red" onClick={() => actions.onRemove(line)}>
          Quitar de la orden
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

/** "Sin cargo" for a zero, like the supplier's list and the comparison. */
function shippingText(line: PurchaseOrderLineOut, currency: string): string {
  return Number(line.shipping_cost) === 0
    ? "Sin cargo"
    : formatMoney(line.shipping_cost, currency);
}

/** What arrived of each line, once the order was issued (HU-22).

 * "Estimado" and "Real" are both about the delivered quantity: the first at the
 * price the line froze, the second off the invoices. Materials only on either
 * side — a delivery's freight is charged once for the whole truck and lives on
 * the receipt, so splitting it per material would invent a number the supplier
 * never wrote (ADR-011 section 8). The caption under the table says so, because
 * a column header cannot. */
function DeliveryLines({
  lines,
  currency,
}: {
  lines: PurchaseOrderLineOut[];
  currency: string;
}) {
  return (
    <Stack gap="xs">
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={760}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Material</Table.Th>
                <Table.Th ta="right">Pedido</Table.Th>
                <Table.Th ta="right">Recibido</Table.Th>
                <Table.Th ta="right">Pendiente</Table.Th>
                <Table.Th ta="right">Estimado</Table.Th>
                <Table.Th ta="right">Real</Table.Th>
                <Table.Th ta="right">Diferencia</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {lines.map((line) => (
                <Table.Tr key={line.id}>
                  <Table.Td>
                    <Text fw={500}>{line.resource.name}</Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatQuantity(line.quantity)} {line.unit.abbreviation}
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatQuantity(line.received_quantity)}{" "}
                    {line.unit.abbreviation}
                  </Table.Td>
                  <Table.Td ta="right">
                    <PendingText line={line} />
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatMoney(line.received_estimate, currency)}
                  </Table.Td>
                  <Table.Td ta="right">
                    <Text fw={600}>
                      {formatMoney(line.actual_cost, currency)}
                    </Text>
                  </Table.Td>
                  <Table.Td ta="right">
                    <DifferenceText line={line} currency={currency} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {lines.map((line) => (
          <Card key={line.id} withBorder padding="sm" radius="md">
            <Stack gap={4}>
              <Text fw={600}>{line.resource.name}</Text>
              <Text size="sm" c="dimmed">
                Recibido {formatQuantity(line.received_quantity)} de{" "}
                {formatQuantity(line.quantity)} {line.unit.abbreviation}
              </Text>
              <Text size="sm" c="dimmed">
                Pendiente: <PendingText line={line} />
              </Text>
              <Group gap="xs" justify="space-between" wrap="nowrap">
                <Text size="sm" c="dimmed">
                  Estimado {formatMoney(line.received_estimate, currency)}
                </Text>
                <Text fw={700}>{formatMoney(line.actual_cost, currency)}</Text>
              </Group>
              <DifferenceText line={line} currency={currency} />
            </Stack>
          </Card>
        ))}
      </Stack>

      <Text size="xs" c="dimmed">
        Estimado y real comparan solo lo recibido: el estimado al precio
        acordado en la orden, el real según las facturas. El envío de cada
        entrega va en su recepción, no repartido por material.
      </Text>
    </Stack>
  );
}

/** "Completo" rather than a zero, which is the thing worth seeing at a glance. */
function PendingText({ line }: { line: PurchaseOrderLineOut }) {
  if (Number(line.pending_quantity) === 0) {
    return (
      <Text span c="obra" fw={600}>
        Completo
      </Text>
    );
  }
  return (
    <Text span>
      {formatQuantity(line.pending_quantity)} {line.unit.abbreviation}
    </Text>
  );
}

/** A dash while nothing arrived: there is nothing to compare yet, and a zero
 * would read as "right on the money". */
function DifferenceText({
  line,
  currency,
}: {
  line: PurchaseOrderLineOut;
  currency: string;
}) {
  if (line.cost_difference === null) {
    return (
      <Text span c="dimmed">
        —
      </Text>
    );
  }
  const { color, prefix } = differenceTone(line.cost_difference);
  return (
    <Text span c={color} fw={600}>
      {prefix}
      {formatMoney(line.cost_difference.replace("-", ""), currency)}
    </Text>
  );
}
