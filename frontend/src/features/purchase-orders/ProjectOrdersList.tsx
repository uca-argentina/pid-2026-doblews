import { Alert, Loader, Stack, Text, Title } from "@mantine/core";
import { OrdersList } from "./OrdersList";
import { useProjectOrders } from "./usePurchaseOrders";

interface ProjectOrdersListProps {
  firmId: number;
  projectId: number;
}

/** The work's orders under its comparison, in every state and newest first
 * (HU-21). Each leads to its own page, where it is edited, issued or
 * cancelled. */
export function ProjectOrdersList({
  firmId,
  projectId,
}: ProjectOrdersListProps) {
  const {
    data: orders,
    isLoading,
    isError,
  } = useProjectOrders(firmId, projectId);

  return (
    <Stack gap="sm">
      <Title order={5}>Órdenes de compra de la obra</Title>

      {isLoading && <Loader size="sm" />}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar las órdenes. Probá de nuevo en un momento.
        </Alert>
      )}

      {orders && orders.length === 0 && (
        <Text size="sm" c="dimmed">
          La obra todavía no tiene órdenes. Elegí materiales en la tabla de
          arriba y tocá "Generar órdenes": se arma un borrador por proveedor.
        </Text>
      )}

      {orders && orders.length > 0 && (
        <OrdersList firmId={firmId} orders={orders} />
      )}
    </Stack>
  );
}
