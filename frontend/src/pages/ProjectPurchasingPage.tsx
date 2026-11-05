import { useState } from "react";
import {
  Alert,
  Anchor,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { ProjectOrdersList } from "../features/purchase-orders/ProjectOrdersList";
import { orderNumber } from "../features/purchase-orders/orderDisplay";
import type { GenerateOrdersOut } from "../features/purchase-orders/types";
import { useGenerateOrders } from "../features/purchase-orders/usePurchaseOrders";
import { canOrder } from "../features/purchasing/orderable";
import { ProjectPurchasingTable } from "../features/purchasing/ProjectPurchasingTable";
import { useProjectPurchasing } from "../features/purchasing/usePurchasing";
import { apiErrorMessage } from "../lib/apiError";

/** HU-18, by work: the cheapest supplier for each material of the take-off.
 *
 * Read only, and about what the work would cost to buy, so it opens to
 * whoever may see its costs — the same rule as the budget (ADR-010 section 6):
 * project.cost.view on the work, or project.view_all for the owner. The client
 * of the work does not see the tab, and gets this notice if they type the URL.
 *
 * HU-20 makes it where orders start: whoever holds purchase_order.manage picks
 * materials and generates one draft per supplier, and the work's orders are
 * listed under the comparison. HU-21 lets them pick the supplier per material
 * before generating, and lists the orders in every state. */
export function ProjectPurchasingPage() {
  const firm = useCurrentFirm();
  const { project, can } = useCurrentProject();

  if (!can("project.cost.view") && !firm.can("project.view_all")) {
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver sus compras.
      </Alert>
    );
  }

  return (
    <PurchasingView
      firmId={firm.firm.id}
      projectId={project.id}
      canSeeSuppliers={firm.can("supplier.view")}
      canSeeOrders={firm.can("purchase_order.view")}
      canManageOrders={firm.can("purchase_order.manage")}
    />
  );
}

function PurchasingView({
  firmId,
  projectId,
  canSeeSuppliers,
  canSeeOrders,
  canManageOrders,
}: {
  firmId: number;
  projectId: number;
  canSeeSuppliers: boolean;
  canSeeOrders: boolean;
  canManageOrders: boolean;
}) {
  const { data, isLoading, isError } = useProjectPurchasing(firmId, projectId);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  // Only the suppliers picked away from the default; the rest go as null, so
  // the backend prices them with the cheapest at that moment.
  const [chosen, setChosen] = useState<Map<number, number>>(new Map());
  const generate = useGenerateOrders(firmId, projectId);

  const toggle = (resourceId: number) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(resourceId)) next.delete(resourceId);
      else next.add(resourceId);
      return next;
    });

  const chooseSupplier = (resourceId: number, supplierId: number) =>
    setChosen((current) => new Map(current).set(resourceId, supplierId));
  const supplierFor = (resourceId: number) => chosen.get(resourceId) ?? null;

  // Only what can still be ordered: a pick left over from before a refetch
  // (now all on order) is not sent.
  const picked = (data?.items ?? []).filter(
    (item) => selected.has(item.resource_id) && canOrder(item),
  );

  const handleGenerate = async () => {
    try {
      const result = await generate.mutateAsync(
        picked.map((item) => ({
          resource_id: item.resource_id,
          supplier_id: supplierFor(item.resource_id),
        })),
      );
      setSelected(new Set());
      setChosen(new Map());
      notifications.show({
        title:
          result.orders.length === 0
            ? "No se generó ninguna orden"
            : "Órdenes en borrador",
        message: generatedMessage(result),
        color: result.orders.length === 0 ? "yellow" : "obra",
      });
    } catch (error) {
      notifications.show({
        title: "No pudimos generar las órdenes",
        message: apiErrorMessage(error, "Probá de nuevo en un momento."),
        color: "red",
      });
    }
  };

  return (
    <Stack gap="md">
      <PageHeader
        order={4}
        title="Compras"
        description="El proveedor más económico para cada material del cómputo, por la cantidad que lleva la obra. Se compara material por material; el presupuesto sigue usando el precio de referencia."
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar las compras. Probá de nuevo en un momento.
        </Alert>
      )}

      {data && data.items.length === 0 && (
        <EmptyState
          title="La obra no tiene materiales en el cómputo"
          to={`/firms/${firmId}/projects/${projectId}/takeoff`}
          linkLabel="Ir al cómputo"
        >
          Cargá el cómputo de la obra para ver a quién conviene comprarle cada
          material.
        </EmptyState>
      )}

      {data && data.items.length > 0 && !data.has_suppliers && (
        <EmptyState
          title="El estudio todavía no tiene proveedores"
          to={canSeeSuppliers ? `/firms/${firmId}/suppliers` : undefined}
          linkLabel="Cargar el primer proveedor"
        >
          Cargá tus proveedores y el precio que te da cada uno, y acá vas a ver
          el más económico para cada material de la obra.
        </EmptyState>
      )}

      {data && data.items.length > 0 && data.has_suppliers && (
        <>
          {canManageOrders && (
            <Group justify="space-between" wrap="wrap" gap="sm">
              <Text size="sm" c="dimmed" style={{ flex: 1, minWidth: 220 }}>
                Elegí materiales y generá las órdenes: se arma un borrador por
                proveedor, con lo que falta pedir. Cada material va al más
                económico, salvo que elijas otro proveedor.
              </Text>
              <Button
                onClick={handleGenerate}
                disabled={picked.length === 0}
                loading={generate.isPending}
              >
                Generar órdenes
                {picked.length > 0 ? ` (${picked.length})` : ""}
              </Button>
            </Group>
          )}
          <ProjectPurchasingTable
            items={data.items}
            currency={data.currency}
            selection={
              canManageOrders
                ? { selected, toggle, supplierFor, chooseSupplier }
                : undefined
            }
          />
          {canSeeOrders && (
            <ProjectOrdersList firmId={firmId} projectId={projectId} />
          )}
        </>
      )}
    </Stack>
  );
}

function EmptyState({
  title,
  children,
  to,
  linkLabel,
}: {
  title: string;
  children: string;
  to?: string;
  linkLabel: string;
}) {
  return (
    <Stack align="center" gap="xs" py="xl">
      <Text fw={600}>{title}</Text>
      <Text size="sm" c="dimmed" ta="center" maw={420}>
        {children}
      </Text>
      {to && (
        <Anchor component={Link} to={to} size="sm">
          {linkLabel} →
        </Anchor>
      )}
    </Stack>
  );
}

/** What generating did, in one sentence per kind of outcome. */
function generatedMessage(result: GenerateOrdersOut): string {
  const parts: string[] = [];
  if (result.orders.length > 0) {
    parts.push(
      `Quedaron en borrador: ${result.orders
        .map((order) => `${orderNumber(order.number)} (${order.supplier.name})`)
        .join(", ")}.`,
    );
  }
  const already = result.skipped.filter((s) => s.reason === "already_ordered");
  const unsold = result.skipped.filter((s) => s.reason === "no_supplier");
  if (already.length > 0) {
    parts.push(
      `Ya estaba todo pedido: ${already.map((s) => s.name).join(", ")}.`,
    );
  }
  if (unsold.length > 0) {
    parts.push(`Sin proveedor: ${unsold.map((s) => s.name).join(", ")}.`);
  }
  return parts.join(" ");
}
