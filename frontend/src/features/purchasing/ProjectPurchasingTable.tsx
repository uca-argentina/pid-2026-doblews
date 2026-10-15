import { Fragment, useState } from "react";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Collapse,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { formatMoney, formatQuantity } from "../../lib/format";
import { cheapestOffers, joinNames } from "./offerDisplay";
import { OffersList } from "./OffersList";
import type { ComparedMaterial } from "./types";

interface ProjectPurchasingTableProps {
  items: ComparedMaterial[];
  currency: string;
}

/** HU-18, by work: each material of the take-off at the quantity the work
 * needs, with the cheapest offer for it and what the budget counts it at.
 *
 * Each row opens to every offer, cheapest first. There is no total for the
 * whole purchase: the comparison is material by material, and adding up each
 * material's winner would read as an optimal purchase, which HU-18 leaves out.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS. */
export function ProjectPurchasingTable({
  items,
  currency,
}: ProjectPurchasingTableProps) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (resourceId: number) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(resourceId)) next.delete(resourceId);
      else next.add(resourceId);
      return next;
    });

  return (
    <>
      <Box visibleFrom="sm">
        <Table.ScrollContainer minWidth={760}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th w={40} />
                <Table.Th>Material</Table.Th>
                <Table.Th ta="right">Cantidad</Table.Th>
                <Table.Th>Más económico</Table.Th>
                <Table.Th ta="right">Costo total</Table.Th>
                <Table.Th ta="right">A precio de referencia</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item) => {
                const expanded = open.has(item.resource_id);
                const offered = item.offers.length > 0;
                return (
                  <Fragment key={item.resource_id}>
                    <Table.Tr>
                      <Table.Td>
                        {offered && (
                          <ActionIcon
                            variant="subtle"
                            color="gray"
                            onClick={() => toggle(item.resource_id)}
                            aria-expanded={expanded}
                            aria-label={`${expanded ? "Ocultar" : "Ver"} los proveedores de ${item.name}`}
                          >
                            {expanded ? "▾" : "▸"}
                          </ActionIcon>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Text fw={500}>{item.name}</Text>
                      </Table.Td>
                      <Table.Td ta="right">
                        {formatQuantity(item.quantity)} {item.unit.abbreviation}
                      </Table.Td>
                      <Table.Td>
                        <Winner item={item} />
                      </Table.Td>
                      <Table.Td ta="right">
                        {offered ? (
                          <Text fw={700}>
                            {formatMoney(item.offers[0].total, currency)}
                          </Text>
                        ) : (
                          <Text c="dimmed">—</Text>
                        )}
                      </Table.Td>
                      <Table.Td ta="right">
                        <Text size="sm" c="dimmed">
                          {formatMoney(item.reference_total, currency)}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {referenceUnitText(item, currency)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                    {expanded && (
                      <Table.Tr>
                        <Table.Td />
                        <Table.Td colSpan={5}>
                          <OffersList
                            offers={item.offers}
                            currency={currency}
                            unitAbbreviation={item.unit.abbreviation}
                          />
                        </Table.Td>
                      </Table.Tr>
                    )}
                  </Fragment>
                );
              })}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Box>

      <Stack gap="sm" hiddenFrom="sm">
        {items.map((item) => {
          const expanded = open.has(item.resource_id);
          const offered = item.offers.length > 0;
          return (
            <Card key={item.resource_id} withBorder padding="md" radius="md">
              <Stack gap={6}>
                <Text fw={600}>{item.name}</Text>
                <Text size="sm" c="dimmed">
                  {formatQuantity(item.quantity)} {item.unit.abbreviation}
                </Text>
                <Winner item={item} />
                {offered && (
                  <Text size="xl" fw={700}>
                    {formatMoney(item.offers[0].total, currency)}
                  </Text>
                )}
                <Text size="sm" c="dimmed">
                  A precio de referencia:{" "}
                  {formatMoney(item.reference_total, currency)} (
                  {referenceUnitText(item, currency)})
                </Text>
                {offered && (
                  <>
                    <Button
                      variant="subtle"
                      size="compact-sm"
                      onClick={() => toggle(item.resource_id)}
                      aria-expanded={expanded}
                      style={{ alignSelf: "flex-start" }}
                    >
                      {expanded
                        ? "Ocultar proveedores"
                        : item.offers.length === 1
                          ? "Ver el proveedor"
                          : `Ver los ${item.offers.length} proveedores`}
                    </Button>
                    <Collapse expanded={expanded}>
                      <OffersList
                        offers={item.offers}
                        currency={currency}
                        unitAbbreviation={item.unit.abbreviation}
                      />
                    </Collapse>
                  </>
                )}
              </Stack>
            </Card>
          );
        })}
      </Stack>
    </>
  );
}

/** The reference price of one unit: what HU-18 shows for a material nobody
 * offers, and what the budget computes with whichever wins. */
function referenceUnitText(item: ComparedMaterial, currency: string): string {
  return `${formatMoney(item.reference_price, currency)} por ${item.unit.abbreviation}`;
}

/** Who wins this material — every one of them, when they tie — or "Sin
 * proveedor" when nobody lists it, in which case the reference price is all
 * there is (HU-18). */
function Winner({ item }: { item: ComparedMaterial }) {
  if (item.offers.length === 0) {
    return (
      <Badge color="gray" variant="light">
        Sin proveedor
      </Badge>
    );
  }
  const winners = cheapestOffers(item.offers);
  return (
    <Text fw={500}>
      {joinNames(winners.map((offer) => offer.supplier_name))}
      {winners.length > 1 && (
        <Text span size="xs" c="dimmed">
          {" "}
          (empatan)
        </Text>
      )}
    </Text>
  );
}
