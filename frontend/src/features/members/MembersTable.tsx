import { Table, Text } from "@mantine/core";
import { MemberStatus } from "./MemberStatus";
import type { MemberOut } from "./types";

/** The roster as a table, for screens wide enough to read one. Mobile gets
 * MemberCard instead (frontend/CLAUDE.md: cards, never a horizontal table).
 *
 * The order is the backend's — active first, then by name — so it does not
 * reshuffle between reloads and does not need sorting here. */
export function MembersTable({ members }: { members: MemberOut[] }) {
  return (
    <Table.ScrollContainer minWidth={600}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Email</Table.Th>
            <Table.Th>Rol</Table.Th>
            <Table.Th>Estado</Table.Th>
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
                <MemberStatus isActive={member.is_active} />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
