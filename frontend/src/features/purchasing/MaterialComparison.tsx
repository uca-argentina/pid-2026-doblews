import { useState } from "react";
import {
  Alert,
  Center,
  Group,
  Loader,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { formatMoney, matchesSearch } from "../../lib/format";
import { useResources } from "../catalog/useCatalog";
import { useCurrentFirm } from "../firms/firmContext";
import { OffersList } from "./OffersList";
import { useMaterialComparison } from "./usePurchasing";

/** HU-18, by material: pick one, type how much of it, and see what each
 * supplier would charge, cheapest first.
 *
 * The quantity is the user's, 1 by default. Changing it asks again — the
 * cheapest depends on it, since shipping is a fixed amount per material — and
 * the list re-orders in place. */
export function MaterialComparison() {
  const { firm } = useCurrentFirm();
  const resources = useResources(firm.id);
  const [resourceId, setResourceId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<number | string>(1);
  // Typing "1500" should ask once, not for 1, 15, 150 and 1500.
  const [settledQuantity] = useDebouncedValue(quantity, 300);

  // Materials only: labour and equipment are on nobody's list (ADR-010
  // section 7), so offering them would only lead to a 422.
  const options = (resources.data ?? [])
    .filter((resource) => resource.type === "material")
    .map((resource) => ({
      value: String(resource.id),
      label: `${resource.name} (${resource.unit.abbreviation})`,
    }));
  const material = resources.data?.find(
    (resource) => String(resource.id) === resourceId,
  );

  const validQuantity =
    typeof settledQuantity === "number" && settledQuantity > 0
      ? String(settledQuantity)
      : null;
  const comparison = useMaterialComparison(
    firm.id,
    resourceId ? Number(resourceId) : null,
    validQuantity,
  );
  // The previous answer is kept while a new quantity is asked for, but not
  // across materials: a list of another material's suppliers would mislead.
  const data =
    comparison.data?.resource_id === Number(resourceId)
      ? comparison.data
      : undefined;

  return (
    <Stack gap="md">
      <Group align="flex-start" gap="sm" grow preventGrowOverflow={false}>
        <Select
          label="Material"
          placeholder={resources.isLoading ? "Cargando…" : "Buscar material"}
          data={options}
          value={resourceId}
          onChange={setResourceId}
          searchable
          // Same search as the catalogue's: accent- and case-insensitive,
          // every word typed has to appear.
          filter={({ options: items, search }) =>
            items.filter(
              (item) => "label" in item && matchesSearch(item.label, search),
            )
          }
          nothingFoundMessage="Ningún material coincide"
          disabled={resources.isLoading || resources.isError}
          error={
            resources.isError ? "No pudimos cargar los materiales" : undefined
          }
          miw={240}
        />
        <NumberInput
          label="Cantidad"
          description={
            material ? `En ${material.unit.abbreviation}` : undefined
          }
          value={quantity}
          onChange={setQuantity}
          min={0}
          decimalScale={3}
          decimalSeparator=","
          thousandSeparator="."
          allowNegative={false}
          hideControls
          inputMode="decimal"
          error={
            typeof quantity === "number" && quantity > 0
              ? undefined
              : "Ingresá una cantidad mayor a cero"
          }
          maw={{ sm: 200 }}
        />
      </Group>

      {!resourceId && (
        <Text size="sm" c="dimmed">
          Elegí un material para ver qué te cobra cada proveedor por esa
          cantidad.
        </Text>
      )}

      {resourceId && !data && comparison.isFetching && (
        <Center>
          <Loader />
        </Center>
      )}

      {comparison.isError && (
        <Alert color="red" variant="light">
          No pudimos comparar este material. Probá de nuevo en un momento.
        </Alert>
      )}

      {resourceId && data && (
        <Stack gap="sm">
          {/* Always said, and always labelled: the price the budget computes
              with is not any supplier's (ADR-010 section 5). */}
          <Text size="sm" c="dimmed">
            Precio de referencia (el del presupuesto):{" "}
            {formatMoney(data.reference_price, data.currency)} por{" "}
            {data.unit.abbreviation}, o{" "}
            {formatMoney(data.reference_total, data.currency)} para esta
            cantidad.
          </Text>

          {data.offers.length === 0 ? (
            <Text size="sm" ta="center" py="md">
              Ningún proveedor del estudio ofrece {data.name}. Cargalo en la
              lista de alguno para poder comparar.
            </Text>
          ) : (
            <OffersList
              offers={data.offers}
              currency={data.currency}
              unitAbbreviation={data.unit.abbreviation}
            />
          )}
        </Stack>
      )}
    </Stack>
  );
}
