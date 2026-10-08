import { Card, Group, Stack, Text } from "@mantine/core";
import { PriceActionsMenu } from "./PriceActionsMenu";
import {
  referencePriceText,
  shippingText,
  supplierPriceText,
  updatedOnText,
} from "./priceDisplay";
import type { SupplierPriceOut } from "./types";

interface PriceCardProps {
  price: SupplierPriceOut;
  onEdit: (price: SupplierPriceOut) => void;
  onRemove: (price: SupplierPriceOut) => void;
}

/** One row of a list on a phone. Same data as a table row, stacked so 375px
 * needs no horizontal scrolling, with each amount labelled by whose price it is. */
export function PriceCard({ price, onEdit, onRemove }: PriceCardProps) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={4}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600}>{price.resource.name}</Text>
          <PriceActionsMenu price={price} onEdit={onEdit} onRemove={onRemove} />
        </Group>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text size="sm" c="dimmed">
            Precio del proveedor
          </Text>
          <Text size="sm" fw={500}>
            {supplierPriceText(price)}
          </Text>
        </Group>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text size="sm" c="dimmed">
            Envío
          </Text>
          <Text size="sm">{shippingText(price)}</Text>
        </Group>
        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text size="sm" c="dimmed">
            Precio de referencia
          </Text>
          <Text size="sm" c="dimmed">
            {referencePriceText(price)}
          </Text>
        </Group>
        <Text size="xs" c="dimmed">
          Actualizado el {updatedOnText(price)}
        </Text>
      </Stack>
    </Card>
  );
}
