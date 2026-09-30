import { useState } from "react";
import { Alert, Box, Button, Center, Loader, Stack } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../features/auth/AuthContext";
import { CreateFirmModal } from "../features/platform/CreateFirmModal";
import { FirmCard } from "../features/platform/FirmCard";
import { FirmStatusModal } from "../features/platform/FirmStatusModal";
import { FirmsTable } from "../features/platform/FirmsTable";
import {
  canOnPlatform,
  PLATFORM_PERMISSIONS,
} from "../features/platform/platformAccess";
import type { FirmAdminOut } from "../features/platform/types";
import { usePlatformFirms } from "../features/platform/usePlatform";

/** HU-7: every firm on the platform, with its head count and its state.
 *
 * Support's home. Suspended firms are listed too, dimmed, because this is
 * where support finds one to reactivate. */
export function PlatformFirmsPage() {
  const { account } = useAuth();
  const { data: firms, isLoading, isError } = usePlatformFirms();
  const [createOpened, createModal] = useDisclosure(false);
  // Which firm the status modal is about, and null when it is closed. Kept
  // here and not in each row, so there is one modal on the screen rather than
  // one per firm — as MembersPage does.
  const [statusTarget, setStatusTarget] = useState<FirmAdminOut | null>(null);

  // Asked separately from the screen's own gate (firm.view): listing firms
  // and creating them are two permissions, even if support holds both today.
  const canCreate = canOnPlatform(account, PLATFORM_PERMISSIONS.createFirm);

  return (
    <Stack gap="md">
      <PageHeader
        title="Estudios"
        description="Los estudios de la plataforma, con su cantidad de miembros y su estado."
        action={
          canCreate ? (
            <Button onClick={createModal.open}>Nuevo estudio</Button>
          ) : undefined
        }
      />

      <CreateFirmModal opened={createOpened} onClose={createModal.close} />
      <FirmStatusModal
        firm={statusTarget}
        onClose={() => setStatusTarget(null)}
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar los estudios. Probá de nuevo en un momento.
        </Alert>
      )}

      {firms && firms.length === 0 && (
        <Alert variant="light" title="Todavía no hay estudios">
          Cuando des de alta el primero, va a aparecer acá.
        </Alert>
      )}

      {firms && firms.length > 0 && (
        <>
          {/* One list, two shapes, switched by CSS as in MembersPage. */}
          <Box visibleFrom="sm">
            <FirmsTable firms={firms} onChangeStatus={setStatusTarget} />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {firms.map((firm) => (
              <FirmCard
                key={firm.id}
                firm={firm}
                onChangeStatus={setStatusTarget}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
