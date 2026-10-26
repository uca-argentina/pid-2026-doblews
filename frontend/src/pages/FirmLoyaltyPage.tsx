import { Alert, Anchor, Center, Loader, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { LevelCard } from "../features/loyalty/LevelCard";
import { PointsHistory } from "../features/loyalty/PointsHistory";
import { useLoyalty } from "../features/loyalty/useLoyalty";

/** HU-24: the firm's level, and every entry behind it.
 *
 * Behind purchase_order.view, like its route: the points come from the orders,
 * so whoever sees the orders sees what they earned, and the client of a firm
 * sees neither (ADR-012 section 6).
 *
 * The level with each supplier is not here. It lives on that supplier's own
 * card, which is where someone asks the question. */
export function FirmLoyaltyPage() {
  const { firm } = useCurrentFirm();
  const { data, isLoading, isError } = useLoyalty(firm.id);

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !data) {
    return (
      <Alert color="red" variant="light" title="No pudimos leer el nivel">
        Probá de nuevo en un momento.
      </Alert>
    );
  }

  return (
    <Stack gap="md">
      <PageHeader
        title="Nivel"
        description="El estudio suma puntos cada vez que le vuelve a comprar a un proveedor, y más si repite el mismo material en una cantidad parecida."
      />

      <LevelCard level={data.firm} title="Nivel del estudio" />

      <Stack gap="xs">
        <Text fw={600}>Historial de puntos</Text>
        {data.history.length === 0 ? (
          <Stack align="center" gap="xs" py="xl">
            <Text c="dimmed">Todavía no recibiste ninguna orden.</Text>
            <Text size="sm" c="dimmed" ta="center">
              Los puntos se suman cuando una orden de compra queda recibida.
            </Text>
            <Anchor component={Link} to={`/firms/${firm.id}/purchase-orders`}>
              Ir a Órdenes de compra
            </Anchor>
          </Stack>
        ) : (
          <PointsHistory firmId={firm.id} entries={data.history} />
        )}
      </Stack>
    </Stack>
  );
}
