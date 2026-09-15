import { useState } from "react";
import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { AdminResourceBrowser } from "../features/catalog-admin/AdminResourceBrowser";
import { DeactivateResourceModal } from "../features/catalog-admin/DeactivateResourceModal";
import { MaterialActionsMenu } from "../features/catalog-admin/MaterialActionsMenu";
import { MaterialFormModal } from "../features/catalog-admin/MaterialFormModal";
import type { ResourceOut } from "../features/catalog-admin/types";

/** HU-8: every material of the system catalogue, administered by support.
 *
 * Its own route and nav entry, separate from "Recetas" — mirrors how HU-7
 * split "Estudios" and "Contraseñas" rather than one screen with a toggle. */
export function PlatformMaterialsPage() {
  // null doubles as "creating", same convention as ProjectFormModal's
  // project prop: it is what the form itself already treats as "new".
  const [editTarget, setEditTarget] = useState<ResourceOut | null>(null);
  const [formOpened, formModal] = useDisclosure(false);
  // Which material the deactivate modal is about, and null when it is
  // closed — one shared modal at page level, same pattern as FirmStatusModal.
  const [deactivateTarget, setDeactivateTarget] = useState<ResourceOut | null>(
    null,
  );

  const openCreate = () => {
    setEditTarget(null);
    formModal.open();
  };
  const openEdit = (resource: ResourceOut) => {
    setEditTarget(resource);
    formModal.open();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <div>
          <Title order={3}>Materiales</Title>
          <Text c="dimmed" size="sm">
            El catálogo de materiales del sistema, igual para todos los
            estudios.
          </Text>
        </div>
        <Button onClick={openCreate}>Nuevo material</Button>
      </Group>

      <MaterialFormModal
        opened={formOpened}
        resource={editTarget}
        onClose={formModal.close}
      />
      <DeactivateResourceModal
        resource={deactivateTarget}
        onClose={() => setDeactivateTarget(null)}
      />

      <AdminResourceBrowser
        renderAction={(resource) => (
          <MaterialActionsMenu
            resource={resource}
            onEdit={openEdit}
            onDeactivate={setDeactivateTarget}
          />
        )}
      />
    </Stack>
  );
}
