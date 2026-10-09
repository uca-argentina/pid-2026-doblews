import { useState } from "react";
import { Button, Card, Group, Stack, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useCurrentFirm } from "../features/firms/firmContext";
import { ArchiveProjectModal } from "../features/projects/ArchiveProjectModal";
import { ProjectFormModal } from "../features/projects/ProjectFormModal";
import { useCurrentProject } from "../features/projects/projectContext";
import { EMPTY, formatDate } from "../features/projects/projectFields";

/** HU-3's detail screen: the data of one work, and the two things that can be
 * done to it.
 *
 * It fetches nothing. ProjectLayout above has already resolved the work from
 * the URL, and the name and client it shows in the header are not repeated
 * here — this is what the header has no room for.
 *
 * Editing and archiving live here and not in that header, which every tab
 * shares: they act on this data, and up there they sat over the take-off and
 * the planning as if they belonged to those. Both are project-scope
 * permissions, carried by the one response that resolved the work — which is
 * why the listing links here instead of offering a menu per row.
 *
 * It is the index route of the work, so HU-6's team and HU-5's take-off become
 * its siblings rather than sections bolted onto it. */
export function ProjectDetailPage() {
  const { firm } = useCurrentFirm();
  const { project, can } = useCurrentProject();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [archiving, setArchiving] = useState(false);

  const canEdit = can("project.edit");
  const canArchive = can("project.archive");

  return (
    <Stack gap="md">
      <PageHeader
        title="Datos"
        order={4}
        action={
          canEdit || canArchive ? (
            <Group gap="sm" wrap="nowrap">
              {canEdit && (
                <Button variant="default" onClick={() => setEditing(true)}>
                  Editar
                </Button>
              )}
              {canArchive && (
                <Button
                  variant="subtle"
                  color="red"
                  onClick={() => setArchiving(true)}
                >
                  Dar de baja
                </Button>
              )}
            </Group>
          ) : undefined
        }
      />

      <Card withBorder padding="lg" radius="md">
        <Stack gap="md">
          <Field label="Dirección">{project.address ?? EMPTY}</Field>
          <Field label="Inicio estimado">
            {formatDate(project.estimated_start_date)}
          </Field>
          <Field label="Descripción">
            {/* The one field here that can hold line breaks, so it is the one
                that keeps them: Mantine has no shorthand for white-space, and
                without this a description typed as paragraphs runs together. */}
            <Text style={{ whiteSpace: "pre-wrap" }}>
              {project.description ?? EMPTY}
            </Text>
          </Field>
        </Stack>
      </Card>

      {/* Rendered only for those who may use them: a modal nobody can open is
          state for nothing. */}
      {canEdit && (
        <ProjectFormModal
          opened={editing}
          project={project}
          onClose={() => setEditing(false)}
        />
      )}
      {canArchive && (
        <ArchiveProjectModal
          opened={archiving}
          project={project}
          onClose={() => setArchiving(false)}
          onArchived={() =>
            navigate(`/firms/${firm.id}/projects`, { replace: true })
          }
        />
      )}
    </Stack>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      {typeof children === "string" ? <Text>{children}</Text> : children}
    </div>
  );
}
