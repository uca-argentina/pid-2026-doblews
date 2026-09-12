import { Anchor, Table, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { EMPTY, formatDate } from "./projectFields";
import type { ProjectSummary } from "./types";

interface ProjectsTableProps {
  projects: ProjectSummary[];
  /** Where one work's own screen lives, given its id. */
  hrefFor: (projectId: number) => string;
}

/** The works as a table, for screens wide enough to read one. Mobile gets
 * ProjectCard instead (frontend/CLAUDE.md: cards, never a horizontal table).
 *
 * The columns are exactly what HU-3 asks the listing to show — "nombre,
 * dirección, fecha estimada de inicio y cliente" — and not the description,
 * which is a paragraph and would push everything else off the row.
 *
 * There is no actions column, unlike the roster. Editing and archiving are
 * project-scope permissions, and only a work's own screen knows whether this
 * caller holds them; offering them here would mean painting buttons that fail
 * for, among others, the owner of the firm on works they are not part of.
 *
 * The order is the backend's — by name, then id — so it does not reshuffle
 * between reloads and does not need sorting here. */
export function ProjectsTable({ projects, hrefFor }: ProjectsTableProps) {
  return (
    <Table.ScrollContainer minWidth={600}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Obra</Table.Th>
            <Table.Th>Dirección</Table.Th>
            <Table.Th>Inicio estimado</Table.Th>
            <Table.Th>Cliente</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {projects.map((project) => (
            <Table.Tr key={project.id}>
              <Table.Td>
                {/* The name is the link, and the only one in the row: a whole
                    clickable row cannot be reached with a keyboard. */}
                <Anchor
                  component={Link}
                  to={hrefFor(project.id)}
                  fw={500}
                  underline="never"
                >
                  {project.name}
                </Anchor>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c={project.address ? undefined : "dimmed"}>
                  {project.address ?? EMPTY}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">
                  {formatDate(project.estimated_start_date)}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c={project.client ? undefined : "dimmed"}>
                  {project.client?.name ?? "Sin cliente"}
                </Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
