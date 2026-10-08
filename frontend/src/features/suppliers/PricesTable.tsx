import { Table, Text } from "@mantine/core";
import { PriceActionsMenu } from "./PriceActionsMenu";
import {
  referencePriceText,
  shippingText,
  supplierPriceText,
  updatedOnText,
} from "./priceDisplay";
import type { SupplierPriceOut } from "./types";

interface PricesTableProps {
  prices: SupplierPriceOut[];
  onEdit: (price: SupplierPriceOut) => void;
  onRemove: (price: SupplierPriceOut) => void;
}

/** A supplier's price list as a table, for screens wide enough to read one.
 * Mobile gets PriceCard instead. The order is the backend's, by material. */
export function PricesTable({ prices, onEdit, onRemove }: PricesTableProps) {
  return (
    <Table.ScrollContainer minWidth={720}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Material</Table.Th>
            <Table.Th ta="right">Precio del proveedor</Table.Th>
            <Table.Th ta="right">Envío</Table.Th>
            <Table.Th ta="right">Precio de referencia</Table.Th>
            <Table.Th>Actualizado</Table.Th>
            <Table.Th w={60} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {prices.map((price) => (
            <Table.Tr key={price.id}>
              <Table.Td>
                <Text fw={500}>{price.resource.name}</Text>
              </Table.Td>
              <Table.Td ta="right">{supplierPriceText(price)}</Table.Td>
              <Table.Td ta="right">{shippingText(price)}</Table.Td>
              <Table.Td ta="right">
                <Text size="sm" c="dimmed">
                  {referencePriceText(price)}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c="dimmed">
                  {updatedOnText(price)}
                </Text>
              </Table.Td>
              <Table.Td>
                <PriceActionsMenu
                  price={price}
                  onEdit={onEdit}
                  onRemove={onRemove}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
