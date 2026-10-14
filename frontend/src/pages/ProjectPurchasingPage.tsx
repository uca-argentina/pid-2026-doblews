import { Alert, Anchor, Center, Loader, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { ProjectPurchasingTable } from "../features/purchasing/ProjectPurchasingTable";
import { useProjectPurchasing } from "../features/purchasing/usePurchasing";

/** HU-18, by work: the cheapest supplier for each material of the take-off.
 *
 * Read only, and about what the work would cost to buy, so it opens to
 * whoever may see its costs — the same rule as the budget (ADR-010 section 6):
 * project.cost.view on the work, or project.view_all for the owner. The client
 * of the work does not see the tab, and gets this notice if they type the URL. */
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
    />
  );
}

function PurchasingView({
  firmId,
  projectId,
  canSeeSuppliers,
}: {
  firmId: number;
  projectId: number;
  canSeeSuppliers: boolean;
}) {
  const { data, isLoading, isError } = useProjectPurchasing(firmId, projectId);

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
        <ProjectPurchasingTable items={data.items} currency={data.currency} />
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
