import { Alert, Card, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { TakeoffLines } from "../features/takeoff/TakeoffLines";
import { TakeoffMaterials } from "../features/takeoff/TakeoffMaterials";
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
  const { canView } = useTakeoffAccess();

  if (!canView) {
    // The tab is already hidden; this answers someone who typed the URL. The
    // backend would refuse the read anyway.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver el cómputo.
      </Alert>
    );
  }

  return <TakeoffView firmId={firm.id} projectId={project.id} />;
}

function TakeoffView({
  firmId,
  projectId,
}: {
  firmId: number;
  projectId: number;
}) {
  const { data: takeoff, isLoading, isError } = useTakeoff(firmId, projectId);

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

  // A take-off with no lines has no materials either. An empty table with its
  // headings would read as something failing to load (same as ProjectsPage).
  if (takeoff.lines.length === 0) {
    return (
      <Card withBorder padding="xl" radius="md">
        <Stack gap={4} align="center">
          <Text fw={500}>Todavía no hay recetas en el cómputo</Text>
          <Text size="sm" c="dimmed" ta="center">
            Cada receta que se carga suma sus materiales al cómputo de la obra.
          </Text>
        </Stack>
      </Card>
    );
  }

  return (
    <Stack gap="xl">
      <Stack gap="sm">
        <Title order={4}>Materiales</Title>
        <TakeoffMaterials takeoff={takeoff} />
      </Stack>

      <Stack gap="sm">
        <Title order={4}>Recetas cargadas</Title>
        <TakeoffLines lines={takeoff.lines} />
      </Stack>
    </Stack>
  );
}
