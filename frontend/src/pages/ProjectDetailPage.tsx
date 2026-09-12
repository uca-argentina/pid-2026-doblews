import { Card, Stack, Text } from "@mantine/core";
import { useCurrentProject } from "../features/projects/projectContext";
import { EMPTY, formatDate } from "../features/projects/projectFields";

/** HU-3's detail screen: the data of one work.
 *
 * It fetches nothing. ProjectLayout above has already resolved the work from
 * the URL, and the name and client it shows in the header are not repeated
 * here — this is what the header has no room for.
 *
 * It is the index route of the work, so HU-6's team and HU-5's take-off become
 * its siblings rather than sections bolted onto it. */
export function ProjectDetailPage() {
  const { project } = useCurrentProject();

  return (
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
