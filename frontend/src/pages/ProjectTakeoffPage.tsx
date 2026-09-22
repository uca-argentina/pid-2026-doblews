import {
  Alert,
  Button,
  Card,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { AddLineModal } from "../features/takeoff/AddLineModal";
import { EditLineModal } from "../features/takeoff/EditLineModal";
import { LineActionsMenu } from "../features/takeoff/LineActionsMenu";
import { RemoveLineModal } from "../features/takeoff/RemoveLineModal";
import { TakeoffLines } from "../features/takeoff/TakeoffLines";
import { TakeoffMaterials } from "../features/takeoff/TakeoffMaterials";
import type { TakeoffLineOut } from "../features/takeoff/types";
import { useTakeoff } from "../features/takeoff/useTakeoff";
import { useTakeoffAccess } from "../features/takeoff/useTakeoffAccess";

/** HU-5: what a work needs and what it costs, and the recipes loaded onto it.
 *
 * A sibling of the work's data under ProjectLayout, which has already resolved
 * the work and the caller's permissions on it: this fetches only the take-off.
 *
 * Materials come first because they are the answer the architect came for;
 * the lines below are how that answer was built, and where it is changed. */
export function ProjectTakeoffPage() {
  const { firm } = useCurrentFirm();
  const { project } = useCurrentProject();
  const { canView, canManage } = useTakeoffAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL. The
    // backend would refuse the read anyway.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver el cómputo.
      </Alert>
    );
  }

  return (
    <TakeoffView
      firmId={firm.id}
      projectId={project.id}
      canManage={canManage}
    />
  );
}

function TakeoffView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: takeoff, isLoading, isError } = useTakeoff(firmId, projectId);
  const [adding, add] = useDisclosure(false);
  // The line each modal is open for; null means that modal is closed.
  const [editing, setEditing] = useState<TakeoffLineOut | null>(null);
  const [removing, setRemoving] = useState<TakeoffLineOut | null>(null);

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !takeoff) {
    return (
      <Alert color="red" variant="light">
        No pudimos cargar el cómputo. Probá de nuevo en un momento.
      </Alert>
    );
  }

  return (
    <>
      {takeoff.lines.length === 0 ? (
        <EmptyTakeoff canManage={canManage} onAdd={add.open} />
      ) : (
        <Stack gap="xl">
          <Stack gap="sm">
            <Title order={4}>Materiales</Title>
            <TakeoffMaterials takeoff={takeoff} />
          </Stack>

          <Stack gap="sm">
            <Group justify="space-between" align="center" wrap="nowrap">
              <Title order={4}>Recetas cargadas</Title>
              {canManage && <Button onClick={add.open}>Agregar receta</Button>}
            </Group>
            <TakeoffLines
              lines={takeoff.lines}
              renderActions={
                canManage
                  ? (line) => (
                      <LineActionsMenu
                        line={line}
                        onEdit={setEditing}
                        onRemove={setRemoving}
                      />
                    )
                  : undefined
              }
            />
          </Stack>
        </Stack>
      )}

      {/* Outside both branches on purpose: adding the first line flips the
          screen from empty to full while the modal is still closing, and a
          modal rendered inside either branch would be torn down mid-way — as
          would removing the last line. Only for those who may manage the
          take-off: a button that fails is worse than none. */}
      {canManage && (
        <>
          <AddLineModal
            opened={adding}
            firmId={firmId}
            projectId={projectId}
            onClose={add.close}
          />
          <EditLineModal
            line={editing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setEditing(null)}
          />
          <RemoveLineModal
            line={removing}
            firmId={firmId}
            projectId={projectId}
            onClose={() => setRemoving(null)}
          />
        </>
      )}
    </>
  );
}

/** A take-off with no lines has no materials either. An empty table with its
 * headings would read as something failing to load (same as ProjectsPage). */
function EmptyTakeoff({
  canManage,
  onAdd,
}: {
  canManage: boolean;
  onAdd: () => void;
}) {
  return (
    <Card withBorder padding="xl" radius="md">
      <Stack gap={4} align="center">
        <Text fw={500}>Todavía no hay recetas en el cómputo</Text>
        <Text size="sm" c="dimmed" ta="center">
          {canManage
            ? "Elegí una receta del catálogo y cargá cuánto lleva la obra: el cómputo suma sus materiales solo."
            : "Vas a ver acá los materiales de la obra cuando se carguen sus recetas."}
        </Text>
        {canManage && (
          <Button mt="sm" onClick={onAdd}>
            Agregar la primera receta
          </Button>
        )}
      </Stack>
    </Card>
  );
}
