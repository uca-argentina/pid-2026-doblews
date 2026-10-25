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
import type { PurchaseOrderLineOut } from "./types";

interface OrderLinesViewProps {
  lines: PurchaseOrderLineOut[];
  currency: string;
  /** Present only while the order is a draft and the caller may manage it. */
  actions?: {
    onQuantity: (line: PurchaseOrderLineOut) => void;
    onSupplier: (line: PurchaseOrderLineOut) => void;
    onRemove: (line: PurchaseOrderLineOut) => void;
  };
}

/** An order's lines, at the price each froze when it was made (ADR-011
 * section 2). A table from sm up and cards below it, both rendered and one
 * hidden by CSS. */
export function OrderLinesView({
  lines,
  currency,
  actions,
}: OrderLinesViewProps) {
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
