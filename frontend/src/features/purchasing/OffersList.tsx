import { Badge, Box, Card, Group, Stack, Table, Text } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { shippingText, updatedOnText } from "./offerDisplay";
import type { OfferOut } from "./types";

interface OffersListProps {
  offers: OfferOut[];
  currency: string;
  /** The material's unit, so a price reads "$ 220,00 por u". */
  unitAbbreviation: string;
}

/** Every supplier's offer for one material, cheapest first, as the backend
 * ordered them. The cheapest is marked — every one of them, when they tie
 * (HU-18).
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS,
 * like the supplier's own price list. */
export function OffersList({
  offers,
  currency,
  unitAbbreviation,
}: OffersListProps) {
  return (
    <>
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Proveedor</Table.Th>
                <Table.Th ta="right">Precio del proveedor</Table.Th>
                <Table.Th ta="right">Envío</Table.Th>
                <Table.Th ta="right">Costo total</Table.Th>
                <Table.Th>Actualizado</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {offers.map((offer) => (
                <Table.Tr
                  key={offer.supplier_id}
                  bg={
                    offer.cheapest
                      ? "var(--mantine-color-obra-light)"
                      : undefined
                  }
                >
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      <Text fw={500}>{offer.supplier_name}</Text>
                      {offer.cheapest && <CheapestBadge />}
                    </Group>
                  </Table.Td>
                  <Table.Td ta="right">
                    {formatMoney(offer.unit_price, currency)} por{" "}
                    {unitAbbreviation}
                  </Table.Td>
                  <Table.Td ta="right">
                    {shippingText(offer, currency)}
                  </Table.Td>
                  <Table.Td ta="right">
                    <Text fw={offer.cheapest ? 700 : 500}>
                      {formatMoney(offer.total, currency)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      {updatedOnText(offer)}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {offers.map((offer) => (
          <Card
            key={offer.supplier_id}
            withBorder
            padding="sm"
            radius="md"
            bg={offer.cheapest ? "var(--mantine-color-obra-light)" : undefined}
          >
            <Stack gap={4}>
              <Group justify="space-between" wrap="nowrap" align="flex-start">
                <Text fw={600}>{offer.supplier_name}</Text>
                {offer.cheapest && <CheapestBadge />}
              </Group>
              <Text size="xl" fw={700}>
                {formatMoney(offer.total, currency)}
              </Text>
              <Text size="sm" c="dimmed">
                {formatMoney(offer.unit_price, currency)} por {unitAbbreviation}{" "}
                · Envío: {shippingText(offer, currency)}
              </Text>
              <Text size="xs" c="dimmed">
                Actualizado el {updatedOnText(offer)}
              </Text>
            </Stack>
          </Card>
        ))}
      </Stack>
    </>
  );
}

function CheapestBadge() {
  return (
    <Badge color="obra" variant="filled" size="sm">
      Más económico
    </Badge>
  );
}
