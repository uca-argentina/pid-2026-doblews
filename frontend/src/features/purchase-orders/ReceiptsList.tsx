import type { ReactNode } from "react";
import { Card, Group, Stack, Text, Title } from "@mantine/core";
import { formatMoney, formatQuantity } from "../../lib/format";
import { formatDateTime, formatDay } from "./orderDisplay";
import type { ReceiptOut } from "./types";

interface ReceiptsListProps {
  receipts: ReceiptOut[];
  currency: string;
  /** Rendered beside the one delivery that may be cancelled, when the caller
   * may manage the order. The backend decides which that is (can_cancel). */
  cancelAction?: (receipt: ReceiptOut) => ReactNode;
}

/** The deliveries of an order, oldest first, each with its day, who loaded it
 * and what it cost (HU-22).
 *
 * A receipt is never edited: what is wrong is cancelled and loaded again, and
 * only the last one, so the list always reads forward (ADR-011 section 3). */
export function ReceiptsList({
  receipts,
  currency,
  cancelAction,
}: ReceiptsListProps) {
  return (
    <Stack gap="sm">
      <Title order={5}>Recepciones</Title>
      {receipts.length === 0 ? (
        <Text size="sm" c="dimmed">
          Todavía no se registró ninguna entrega de esta orden.
        </Text>
      ) : (
        receipts.map((receipt) => (
          <Card key={receipt.id} withBorder padding="sm" radius="md">
            <Stack gap="xs">
              <Group justify="space-between" align="baseline" wrap="wrap">
                <Text fw={600}>{formatDay(receipt.received_on)}</Text>
                <Text fw={700}>{formatMoney(receipt.total, currency)}</Text>
              </Group>

              <Stack gap={2}>
                {receipt.lines.map((line) => (
                  <Text key={line.purchase_order_line_id} size="sm">
                    {line.resource.name}: {formatQuantity(line.quantity)}{" "}
                    {line.unit.abbreviation} ·{" "}
                    {formatMoney(line.actual_cost, currency)}
                  </Text>
                ))}
                {receipt.shipping_cost !== null && (
                  <Text size="sm" c="dimmed">
                    Envío de la entrega:{" "}
                    {formatMoney(receipt.shipping_cost, currency)}
                  </Text>
                )}
              </Stack>

              {receipt.note && (
                <Text size="sm" c="dimmed">
                  {receipt.note}
                </Text>
              )}

              <Group justify="space-between" align="center" wrap="wrap">
                <Text size="xs" c="dimmed">
                  Cargada por {receipt.created_by.name} el{" "}
                  {formatDateTime(receipt.created_at)}
                </Text>
                {receipt.can_cancel && cancelAction?.(receipt)}
              </Group>
            </Stack>
          </Card>
        ))
      )}
    </Stack>
  );
}
