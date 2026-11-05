import {
  Alert,
  Card,
  Center,
  Loader,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import { PageHeader } from "../../components/PageHeader";
import { ProjectOverviewCard } from "./ProjectOverviewCard";
import { useProjectsOverview } from "./useProjects";

/** "Mis obras" (HU-26): the works someone follows without running them, each
 * at a glance. Which works is the backend's answer, as on the listing. */
export function MyProjectsView({
  firmId,
  firmName,
}: {
  firmId: number;
  firmName: string;
}) {
  const { data: works, isLoading, isError } = useProjectsOverview(firmId);

  return (
    <Stack gap="md">
      <PageHeader
        title="Mis obras"
        description={`Cómo vienen tus obras con ${firmName}.`}
      />

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar tus obras. Probá de nuevo en un momento.
        </Alert>
      )}

      {works?.length === 0 && (
        <Card withBorder padding="xl" radius="md">
          <Stack gap={4} align="center">
            <Text fw={500}>Todavía no tenés obras asignadas</Text>
            <Text size="sm" c="dimmed" ta="center">
              Cuando el estudio te sume a una obra, la vas a ver acá con su
              avance y su presupuesto.
            </Text>
          </Stack>
        </Card>
      )}

      {works && works.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="md">
          {works.map((work) => (
            <ProjectOverviewCard
              key={work.id}
              work={work}
              workPath={`/firms/${firmId}/projects/${work.id}`}
            />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}
