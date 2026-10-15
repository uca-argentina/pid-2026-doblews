import { useState } from "react";
import {
  Alert,
  Anchor,
  Box,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { DeactivateSupplierModal } from "../features/suppliers/DeactivateSupplierModal";
import { PriceCard } from "../features/suppliers/PriceCard";
import { PriceFormModal } from "../features/suppliers/PriceFormModal";
import { PricesTable } from "../features/suppliers/PricesTable";
import { RemovePriceModal } from "../features/suppliers/RemovePriceModal";
import { SupplierActionsMenu } from "../features/suppliers/SupplierActionsMenu";
import { SupplierFormModal } from "../features/suppliers/SupplierFormModal";
import { useSupplier } from "../features/suppliers/useSuppliers";
import type {
  SupplierOut,
  SupplierPriceOut,
} from "../features/suppliers/types";

/** HU-17: one supplier and its price list.
 *
 * Another firm's supplier and one that was given up answer 404, and both read
 * here as "no encontramos este proveedor": a firm never learns which ids exist
 * elsewhere. */
export function SupplierDetailPage() {
  const { firm, can } = useCurrentFirm();
  const navigate = useNavigate();
  const params = useParams();
  const supplierId = Number(params.supplierId);
  const {
    data: supplier,
    isLoading,
    isError,
  } = useSupplier(firm.id, supplierId);
  const canManage = can("supplier.manage");

  const [editOpened, editModal] = useDisclosure(false);
  const [deactivateTarget, setDeactivateTarget] = useState<SupplierOut | null>(
    null,
  );
  // null doubles as "adding", same convention as the supplier form.
  const [priceTarget, setPriceTarget] = useState<SupplierPriceOut | null>(null);
  const [priceFormOpened, priceFormModal] = useDisclosure(false);
  const [removeTarget, setRemoveTarget] = useState<SupplierPriceOut | null>(
    null,
  );

  const backToList = (
    <Anchor component={Link} to={`/firms/${firm.id}/suppliers`} size="sm">
      ← Proveedores
    </Anchor>
  );

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !supplier) {
    return (
      <Stack gap="md">
        {backToList}
        <Alert color="red" variant="light">
          No encontramos este proveedor. Puede haber sido dado de baja.
        </Alert>
      </Stack>
    );
  }

  const openAdd = () => {
    setPriceTarget(null);
    priceFormModal.open();
  };
  const openEditPrice = (price: SupplierPriceOut) => {
    setPriceTarget(price);
    priceFormModal.open();
  };

  const contact = [
    supplier.contact_name,
    supplier.phone,
    supplier.contact_email,
    supplier.address,
  ].filter(Boolean);

  return (
    <Stack gap="md">
      {backToList}

      <PageHeader
        title={supplier.name}
        description={contact.length > 0 ? contact.join(" · ") : undefined}
        action={
          <SupplierActionsMenu
            supplier={supplier}
            onEdit={editModal.open}
            onDeactivate={setDeactivateTarget}
          />
        }
      />

      <SupplierFormModal
        opened={editOpened}
        supplier={supplier}
        onClose={editModal.close}
      />
      <DeactivateSupplierModal
        supplier={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
        onDone={() => navigate(`/firms/${firm.id}/suppliers`)}
      />
      <PriceFormModal
        opened={priceFormOpened}
        supplierId={supplier.id}
        price={priceTarget}
        listedResourceIds={supplier.prices.map((price) => price.resource.id)}
        onClose={priceFormModal.close}
      />
      <RemovePriceModal
        supplierId={supplier.id}
        price={removeTarget}
        onClose={() => setRemoveTarget(null)}
      />

      <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm">
        <div>
          <Text fw={600}>Lista de precios</Text>
          <Text size="sm" c="dimmed">
            Lo que cobra este proveedor por cada material, junto al precio de
            referencia con el que se presupuesta.
          </Text>
        </div>
        {canManage && <Button onClick={openAdd}>Agregar material</Button>}
      </Group>

      {supplier.prices.length === 0 ? (
        <Stack align="center" gap="xs" py="xl">
          <Text fw={600}>Esta lista todavía no tiene materiales</Text>
          <Text size="sm" c="dimmed" ta="center" maw={420}>
            Agregá los materiales que te vende, con su precio y su costo de
            envío.
          </Text>
          {canManage && (
            <Button mt="xs" onClick={openAdd}>
              Agregar el primer material
            </Button>
          )}
        </Stack>
      ) : (
        <>
          <Box visibleFrom="sm">
            <PricesTable
              prices={supplier.prices}
              onEdit={openEditPrice}
              onRemove={setRemoveTarget}
            />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {supplier.prices.map((price) => (
              <PriceCard
                key={price.id}
                price={price}
                onEdit={openEditPrice}
                onRemove={setRemoveTarget}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
