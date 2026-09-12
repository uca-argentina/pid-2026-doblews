import {
  Alert,
  Box,
  Card,
  Center,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useCurrentFirm } from "../features/firms/firmContext";
import { ProjectCard } from "../features/projects/ProjectCard";
import { ProjectsTable } from "../features/projects/ProjectsTable";
import { useProjects } from "../features/projects/useProjects";

/** HU-3: the works of this firm, with their address, start date and client.
 *
 * Which works appear is the backend's answer and not a filter applied here: an
 * architect sees the ones they are on, and the owner sees every work of the
 * firm because they hold project.view_all. Neither ever sees another firm's.
 *
 * The firm comes already resolved from FirmLayout, which also answers a
 * foreign firm id with "not found" before this ever renders. */
export function ProjectsPage() {
  const { firm } = useCurrentFirm();
  const { data: projects, isLoading, isError } = useProjects(firm.id);

  const hrefFor = (projectId: number) =>
    `/firms/${firm.id}/projects/${projectId}`;

  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Obras</Title>
        <Text c="dimmed" size="sm">
          Las obras de {firm.name} en las que participás.
        </Text>
      </div>

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar las obras. Probá de nuevo en un momento.
        </Alert>
      )}

      {/* Unlike the roster, which always has at least its owner, a firm really
          does start with no works at all — and this is the first screen an
          architect lands on after logging in. An empty table with four
          headings would read as something failing to load. */}
      {projects?.length === 0 && (
        <Card withBorder padding="xl" radius="md">
          <Stack gap={4} align="center">
            <Text fw={500}>Todavía no hay obras</Text>
            <Text size="sm" c="dimmed" ta="center">
              Cada obra guarda por separado sus datos, su equipo y su cómputo.
            </Text>
          </Stack>
        </Card>
      )}

      {projects && projects.length > 0 && (
        <>
          {/* One list, two shapes. Both are rendered and one is hidden by CSS,
              which is how Mantine's responsive props work: no window
              measurement, and nothing to re-render on resize. */}
          <Box visibleFrom="sm">
            <ProjectsTable projects={projects} hrefFor={hrefFor} />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                hrefFor={hrefFor}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
