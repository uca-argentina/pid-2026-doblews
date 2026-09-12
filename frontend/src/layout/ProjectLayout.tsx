import { useEffect, useMemo, useState } from "react";
import {
  Anchor,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link, Outlet, useNavigate, useParams } from "react-router-dom";
import { useCurrentFirm } from "../features/firms/firmContext";
import { ArchiveProjectModal } from "../features/projects/ArchiveProjectModal";
import { ProjectFormModal } from "../features/projects/ProjectFormModal";
import {
  ProjectContext,
  type CurrentProject,
} from "../features/projects/projectContext";
import { useProject } from "../features/projects/useProjects";

const NOT_FOUND = "No encontramos esa obra, o no formás parte de ella.";

/** Everything under /firms/:firmId/projects/:projectId: resolves the work once,
 * then hands it to every screen inside through useCurrentProject().
 *
 * It exists because HU-3 asks for the name to stay visible "como contexto en
 * toda la navegación interna" of a work, and because HU-6 (team) and HU-5
 * (take-off) go inside this screen: as child routes they get the work and the
 * caller's permissions on it without fetching either again.
 *
 * The header is also the only place the actions live. Editing and archiving
 * are project-scope permissions, and this is the one response that carries
 * them — which is why the listing links here instead of offering a menu per
 * row.
 *
 * Unlike FirmLayout, which renders an explanation in place, a work that cannot
 * be seen sends the caller back to the listing. The difference is deliberate:
 * a firm that is not yours is the end of the road, while a work that is not
 * yours has a listing of your own one click up, and leaving someone on a dead
 * URL inside a firm they do belong to reads as the app breaking. Either way
 * the message is the same and says nothing about whether the work exists
 * (HU-3: 404, "no revelamos que existe"). */
export function ProjectLayout() {
  const { firm } = useCurrentFirm();
  const { projectId: param = "" } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  // Numeric from here down, so the query key matches the one the listing
  // invalidates. A URL like /projects/abc never reaches the API: useProject
  // leaves the query disabled and it is answered below exactly like a work
  // that is not yours, which is what the backend would say anyway.
  const projectId = Number(param);
  const isValidId = Number.isInteger(projectId) && projectId > 0;

  const { data: project, isLoading, isError } = useProject(firm.id, projectId);

  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const listingPath = `/firms/${firm.id}/projects`;
  const unreachable = !isValidId || isError;

  // In an effect and not during render: navigate() and notifications.show()
  // both change state elsewhere, and React forbids that while rendering.
  useEffect(() => {
    if (!unreachable) return;
    notifications.show({
      title: "Obra no encontrada",
      message: NOT_FOUND,
      color: "red",
    });
    navigate(listingPath, { replace: true });
  }, [unreachable, navigate, listingPath]);

  const current = useMemo<CurrentProject | null>(() => {
    if (!project) return null;
    const granted = new Set(project.permissions);
    return { project, can: (permission) => granted.has(permission) };
  }, [project]);

  if (unreachable) {
    // The effect above is already on its way to the listing; rendering the
    // loader avoids a frame of empty screen.
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isLoading || !current) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  return (
    <ProjectContext.Provider value={current}>
      <Stack gap="md">
        <div>
          {/* The way back, and what tells the reader which listing this work
              belongs to. The sidebar already highlights "Obras", because its
              active check uses startsWith and this route sits under it. */}
          <Anchor component={Link} to={listingPath} size="sm" c="dimmed">
            ← Obras
          </Anchor>
        </div>

        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <div>
            <Title order={3}>{current.project.name}</Title>
            <Text c="dimmed" size="sm">
              {current.project.client
                ? `Cliente: ${current.project.client.name}`
                : "Sin cliente asignado"}
            </Text>
          </div>

          <Group gap="sm" wrap="nowrap">
            {current.can("project.edit") && (
              <Button variant="default" onClick={() => setEditing(true)}>
                Editar
              </Button>
            )}
            {current.can("project.archive") && (
              <Button
                variant="subtle"
                color="red"
                onClick={() => setArchiving(true)}
              >
                Dar de baja
              </Button>
            )}
          </Group>
        </Group>

        <ProjectFormModal
          opened={editing}
          project={current.project}
          onClose={() => setEditing(false)}
        />
        <ArchiveProjectModal
          opened={archiving}
          project={current.project}
          onClose={() => setArchiving(false)}
          onArchived={() => navigate(listingPath, { replace: true })}
        />

        {/* HU-6's team and HU-5's take-off become siblings of the index route
            here, and read the work from the context above. */}
        <Outlet />
      </Stack>
    </ProjectContext.Provider>
  );
}
