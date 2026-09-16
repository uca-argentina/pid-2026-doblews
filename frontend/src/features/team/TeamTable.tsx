import { Table, Text } from "@mantine/core";
import dayjs from "dayjs";
import { TeamActionsMenu } from "./TeamActionsMenu";
import { TeamMemberStatus } from "./TeamMemberStatus";
import type { ProjectMemberOut } from "./types";

interface TeamTableProps {
  members: ProjectMemberOut[];
  onChangeRole: (member: ProjectMemberOut) => void;
  onRemove: (member: ProjectMemberOut) => void;
}

/** The team as a table, for screens wide enough to read one. Mobile gets
 * TeamMemberCard instead (frontend/CLAUDE.md: cards, never a horizontal
 * table).
 *
 * The order is the backend's — people still in the studio first, the lead at
 * the top of them, then by name — so it does not reshuffle between reloads
 * and does not need sorting here. */
export function TeamTable({ members, onChangeRole, onRemove }: TeamTableProps) {
  return (
    <Table.ScrollContainer minWidth={700}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Email</Table.Th>
            <Table.Th>Rol en la obra</Table.Th>
            <Table.Th>Alta</Table.Th>
            <Table.Th>Estado</Table.Th>
            {/* The actions column has no heading, as in the roster: "Acciones"
                would name the ⋯ button rather than the column, and the button
                already says who it belongs to through its aria-label. */}
            <Table.Th w={60} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {members.map((member) => (
            <Table.Tr
              key={member.account_id}
              opacity={member.is_active ? 1 : 0.6}
            >
              <Table.Td>
                <Text fw={500}>{member.name}</Text>
              </Table.Td>
              <Table.Td>
                <Text c="dimmed" size="sm">
                  {member.email}
                </Text>
              </Table.Td>
              <Table.Td>{member.role.name}</Table.Td>
              <Table.Td>
                <Text size="sm">
                  {dayjs(member.joined_at).format("DD/MM/YYYY")}
                </Text>
              </Table.Td>
              <Table.Td>
                <TeamMemberStatus isActive={member.is_active} />
              </Table.Td>
              <Table.Td>
                <TeamActionsMenu
                  member={member}
                  onChangeRole={onChangeRole}
                  onRemove={onRemove}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
