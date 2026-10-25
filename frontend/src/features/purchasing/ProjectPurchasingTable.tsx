import { Fragment, useState } from "react";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Collapse,
  Group,
  Select,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { formatMoney, formatQuantity } from "../../lib/format";
import { cheapestOffers, joinNames } from "./offerDisplay";
import { OffersList } from "./OffersList";
import { canOrder, offerTotalFor, pendingQuantity } from "./orderable";
import type {
  ComparedMaterial,
  OfferOut,
  ProjectPurchasingItem,
} from "./types";

/** Picking materials to order (HU-20) and the supplier for each (HU-21), for
 * whoever may generate orders. */
export interface MaterialSelection {
  selected: Set<number>;
  toggle: (resourceId: number) => void;
  /** The supplier picked for a material, or null for the default: the cheapest. */
  supplierFor: (resourceId: number) => number | null;
  chooseSupplier: (resourceId: number, supplierId: number) => void;
}

interface ProjectPurchasingTableProps {
  items: ProjectPurchasingItem[];
  currency: string;
  /** Present only for whoever holds purchase_order.manage. */
  selection?: MaterialSelection;
}

/** HU-18, by work: each material of the take-off at the quantity the work
 * needs, with the cheapest offer for it and what the budget counts it at.
 *
 * Each row opens to every offer, cheapest first. There is no total for the
 * whole purchase: the comparison is material by material, and adding up each
 * material's winner would read as an optimal purchase, which HU-18 leaves out.
 *
 * HU-20 adds, under each quantity, how much is already on order, and — for
 * whoever may generate orders — a checkbox to pick the materials to order. A
 * material nobody sells, or already all on order, cannot be picked.
 *
 * HU-21 lets whoever orders pick the supplier: where a material can be
 * ordered, the cheapest becomes a picker with every offer, the cheapest chosen
 * by default, each priced for what the work still has to order. The cost then
 * follows the supplier picked.
 *
 * A table from sm up and cards below it, both rendered and one hidden by CSS. */
export function ProjectPurchasingTable({
  items,
  currency,
  selection,
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
                {selection && <Table.Th w={40} />}
                <Table.Th w={40} />
                <Table.Th>Material</Table.Th>
                <Table.Th ta="right">Cantidad</Table.Th>
                <Table.Th>{selection ? "Proveedor" : "Más económico"}</Table.Th>
                <Table.Th ta="right">Costo total</Table.Th>
                <Table.Th ta="right">A precio de referencia</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item) => {
                const expanded = open.has(item.resource_id);
                const chosen = chosenOffer(item, selection);
                return (
                  <Fragment key={item.resource_id}>
                    <Table.Tr>
                      {selection && (
                        <Table.Td>
                          <SelectBox item={item} selection={selection} />
                        </Table.Td>
                      )}
                      <Table.Td>
                        {item.offers.length > 0 && (
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
                        <OrderedNote item={item} />
                      </Table.Td>
                      <Table.Td>
                        <SupplierCell
                          item={item}
                          currency={currency}
                          selection={selection}
                        />
                      </Table.Td>
                      <Table.Td ta="right">
                        {chosen ? (
                          <Text fw={700}>
                            {formatMoney(chosen.total, currency)}
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
                        <Table.Td colSpan={selection ? 2 : 1} />
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
          const chosen = chosenOffer(item, selection);
          return (
            <Card key={item.resource_id} withBorder padding="md" radius="md">
              <Stack gap={6}>
                <Group justify="space-between" wrap="nowrap" align="flex-start">
                  <Text fw={600}>{item.name}</Text>
                  {selection && <SelectBox item={item} selection={selection} />}
                </Group>
                <Text size="sm" c="dimmed">
                  {formatQuantity(item.quantity)} {item.unit.abbreviation}
                </Text>
                <OrderedNote item={item} />
                <SupplierCell
                  item={item}
                  currency={currency}
                  selection={selection}
                />
                {chosen && (
                  <Text size="xl" fw={700}>
                    {formatMoney(chosen.total, currency)}
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

/** The offer a row prices: the supplier picked, or the cheapest. */
function chosenOffer(
  item: ProjectPurchasingItem,
  selection?: MaterialSelection,
): OfferOut | undefined {
  const picked = selection?.supplierFor(item.resource_id);
  return (
    item.offers.find((offer) => offer.supplier_id === picked) ?? item.offers[0]
  );
}

/** The picker where the material can be ordered by whoever orders; who wins
 * it, everywhere else. */
function SupplierCell({
  item,
  currency,
  selection,
}: {
  item: ProjectPurchasingItem;
  currency: string;
  selection?: MaterialSelection;
}) {
  if (!selection || !canOrder(item)) return <Winner item={item} />;
  const pending = pendingQuantity(item);
  return (
    <Select
      aria-label={`Proveedor de ${item.name}`}
      data={item.offers.map((offer) => ({
        value: String(offer.supplier_id),
        label: `${offer.supplier_name} — ${formatMoney(
          String(offerTotalFor(offer, pending)),
          currency,
        )}${offer.cheapest ? " (más económico)" : ""}`,
      }))}
      value={String(chosenOffer(item, selection)!.supplier_id)}
      onChange={(value) => {
        if (value) selection.chooseSupplier(item.resource_id, Number(value));
      }}
      // The options price what is left to order; say so when that is not the
      // whole quantity the row shows.
      description={
        Number(item.ordered_quantity) > 0
          ? `Por lo que falta pedir: ${formatQuantity(String(pending))} ${item.unit.abbreviation}`
          : undefined
      }
      allowDeselect={false}
      comboboxProps={{ withinPortal: true }}
      miw={240}
    />
  );
}

/** "Ya pedido: 7.200 u" under the quantity, when something is on order. */
function OrderedNote({ item }: { item: ProjectPurchasingItem }) {
  if (Number(item.ordered_quantity) <= 0) return null;
  return (
    <Text size="xs" c="dimmed">
      Ya pedido: {formatQuantity(item.ordered_quantity)}{" "}
      {item.unit.abbreviation}
    </Text>
  );
}

function SelectBox({
  item,
  selection,
}: {
  item: ProjectPurchasingItem;
  selection: MaterialSelection;
}) {
  const orderable = canOrder(item);
  return (
    <Checkbox
      checked={orderable && selection.selected.has(item.resource_id)}
      onChange={() => selection.toggle(item.resource_id)}
      disabled={!orderable}
      aria-label={
        orderable
          ? `Elegir ${item.name} para la orden`
          : `${item.name}: ${item.offers.length === 0 ? "sin proveedor" : "ya está todo pedido"}`
      }
    />
  );
}
