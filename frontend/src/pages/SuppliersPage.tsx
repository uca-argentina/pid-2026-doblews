import { useState } from "react";
import { Alert, Box, Button, Center, Loader, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { DeactivateSupplierModal } from "../features/suppliers/DeactivateSupplierModal";
import { SupplierCard } from "../features/suppliers/SupplierCard";
import { SupplierFormModal } from "../features/suppliers/SupplierFormModal";
import { SuppliersTable } from "../features/suppliers/SuppliersTable";
import { useSuppliers } from "../features/suppliers/useSuppliers";
import type { SupplierOut } from "../features/suppliers/types";

/** HU-17: the firm's suppliers, each leading to its own price list.
 *
 * The whole screen sits behind supplier.view; creating, editing and giving up
 * a supplier need supplier.manage, which today the same roles hold. The client
 * of a firm holds neither, and never gets here. */
export function SuppliersPage() {
  const { firm, can } = useCurrentFirm();
  const navigate = useNavigate();
  const { data: suppliers, isLoading, isError } = useSuppliers(firm.id);
  const canManage = can("supplier.manage");

  // null doubles as "creating", same convention as CatalogPage.
  const [editTarget, setEditTarget] = useState<SupplierOut | null>(null);
  const [formOpened, formModal] = useDisclosure(false);
  const [deactivateTarget, setDeactivateTarget] = useState<SupplierOut | null>(
    null,
  );

  const openCreate = () => {
    setEditTarget(null);
    formModal.open();
  };
  const openEdit = (supplier: SupplierOut) => {
    setEditTarget(supplier);
    formModal.open();
  };

  return (
    <Stack gap="md">
      <PageHeader
        title="Proveedores"
        description="A quién le comprás y a qué precio. Estos precios sirven para comparar compras; el presupuesto de las obras sigue usando el precio de referencia."
        action={
          canManage ? (
            <Button onClick={openCreate}>Nuevo proveedor</Button>
          ) : undefined
        }
      />

      <SupplierFormModal
        opened={formOpened}
        supplier={editTarget}
        onClose={formModal.close}
        // A new supplier is useless until it has a list, so go there.
        onSaved={(saved) => {
          if (!editTarget) navigate(`/firms/${firm.id}/suppliers/${saved.id}`);
        }}
      />
      <DeactivateSupplierModal
        supplier={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar los proveedores. Probá de nuevo en un momento.
        </Alert>
      )}

      {suppliers && suppliers.length === 0 && (
        <Stack align="center" gap="xs" py="xl">
          <Text fw={600}>Todavía no cargaste ningún proveedor</Text>
          <Text size="sm" c="dimmed" ta="center" maw={420}>
            Cargá el primero y el precio que te da por cada material, para saber
            cuánto te sale de verdad comprar.
          </Text>
          {canManage && (
            <Button mt="xs" onClick={openCreate}>
              Cargar el primer proveedor
            </Button>
          )}
        </Stack>
      )}

      {suppliers && suppliers.length > 0 && (
        <>
          {/* One list, two shapes. Both are rendered and one is hidden by CSS,
              which is how Mantine's responsive props work. */}
          <Box visibleFrom="sm">
            <SuppliersTable
              firmId={firm.id}
              suppliers={suppliers}
              onEdit={openEdit}
              onDeactivate={setDeactivateTarget}
            />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {suppliers.map((supplier) => (
              <SupplierCard
                key={supplier.id}
                firmId={firm.id}
                supplier={supplier}
                onEdit={openEdit}
                onDeactivate={setDeactivateTarget}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
