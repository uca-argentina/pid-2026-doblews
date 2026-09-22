import { useEffect, useMemo, useState } from "react";
import {
  Anchor,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  Link,
  Outlet,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useCurrentFirm } from "../features/firms/firmContext";
import { ArchiveProjectModal } from "../features/projects/ArchiveProjectModal";
import { ProjectFormModal } from "../features/projects/ProjectFormModal";
import {
  ProjectContext,
  type CurrentProject,
} from "../features/projects/projectContext";
import { useProject } from "../features/projects/useProjects";
import type { ProjectDetail } from "../features/projects/types";

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
  const { firm, can } = useCurrentFirm();
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

        <ProjectTabs
          basePath={`${listingPath}/${current.project.id}`}
          project={current.project}
          firmCan={can}
        />

        {/* The tab's own screen, reading the work from the context above. */}
        <Outlet />
      </Stack>
    </ProjectContext.Provider>
  );
}

interface ProjectTabsProps {
  /** The work's own URL, /firms/:firmId/projects/:projectId. */
  basePath: string;
  project: ProjectDetail;
  firmCan: (permission: string) => boolean;
}

/** The sections of one work, as tabs that are routes.
 *
 * Routes and not local state, so a take-off can be linked to and survives a
 * reload, and so each section is a child of this layout as HU-3 left it ready
 * for: HU-6's team becomes one more entry here.
 *
 * The take-off tab follows the same rule as useTakeoffAccess — a permission on
 * the work, or the owner's project.view_all on the firm. It is spelled out
 * here rather than calling that hook because the hook reads the project
 * context, and this renders inside the component that provides it.
 *
 * With only the data tab to show there are no tabs at all: a single tab is a
 * heading pretending to be navigation. */
function ProjectTabs({ basePath, project, firmCan }: ProjectTabsProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  // Two names per tab on purpose. `value` identifies the tab to Mantine, which
  // refuses an empty string: it builds DOM ids from it and throws "rendered
  // with invalid value" on "", blanking the whole work screen. `path` is the
  // URL segment, and the data tab is the index route, whose segment really is
  // "". Using one for both is what broke.
  const tabs = [
    { value: "data", path: "", label: "Datos", visible: true },
    {
      value: "takeoff",
      path: "takeoff",
      label: "Cómputo",
      visible:
        project.permissions.includes("project.recipe.view") ||
        firmCan("project.view_all"),
    },
    {
      value: "team",
      path: "team",
      label: "Equipo",
      // No project.view_all fallback, unlike the take-off above, and that is
      // the rule rather than an omission: project.member.view is not granted
      // by the firm (ADR-002 section 7), so the owner of a work they are not
      // on would open a tab the backend answers with a 403.
      visible: project.permissions.includes("project.member.view"),
    },
  ].filter((tab) => tab.visible);

  if (tabs.length < 2) {
    return null;
  }

  // The segment after the work's id, or "" on the index. Anything unknown
  // falls back to the data tab rather than to no tab selected.
  const segment = pathname.slice(basePath.length).split("/")[1] ?? "";
  const active = tabs.find((tab) => tab.path === segment) ?? tabs[0];

  return (
    <Tabs
      value={active.value}
      onChange={(value) => {
        const target = tabs.find((tab) => tab.value === value);
        if (!target) return;
        navigate(target.path ? `${basePath}/${target.path}` : basePath);
      }}
    >
      <Tabs.List>
        {tabs.map((tab) => (
          <Tabs.Tab key={tab.value} value={tab.value}>
            {tab.label}
          </Tabs.Tab>
        ))}
      </Tabs.List>
    </Tabs>
  );
}
