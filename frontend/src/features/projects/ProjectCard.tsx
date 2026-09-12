import { Anchor, Card, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { EMPTY, formatDate } from "./projectFields";
import type { ProjectSummary } from "./types";

interface ProjectCardProps {
  project: ProjectSummary;
  hrefFor: (projectId: number) => string;
}

/** One work on a phone. The same four fields as a table row, stacked instead
 * of side by side, so 375px needs no horizontal scrolling.
 *
 * The address is truncated rather than wrapped: it is the longest field by far
 * and letting it wrap pushes the rest of the card around. The date and the
 * client share the last line, which is what keeps a card three lines tall
 * whatever it holds. */
export function ProjectCard({ project, hrefFor }: ProjectCardProps) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={4}>
        <Anchor
          component={Link}
          to={hrefFor(project.id)}
          fw={600}
          underline="never"
        >
          <Text fw={600} truncate>
            {project.name}
          </Text>
        </Anchor>

        <Text size="sm" c="dimmed" truncate>
          {project.address ?? EMPTY}
        </Text>

        <Group justify="space-between" gap="xs" wrap="nowrap">
          <Text size="sm">{formatDate(project.estimated_start_date)}</Text>
          <Text size="sm" c={project.client ? undefined : "dimmed"} truncate>
            {project.client?.name ?? "Sin cliente"}
          </Text>
        </Group>
      </Stack>
    </Card>
  );
}
