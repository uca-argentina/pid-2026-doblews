import { Table, Text } from "@mantine/core";
import { FirmStatus } from "./FirmStatus";
import type { FirmAdminOut } from "./types";

interface FirmsTableProps {
  firms: FirmAdminOut[];
}

/** The platform's firms as a table, for screens wide enough to read one.
 * Mobile gets FirmCard instead (frontend/CLAUDE.md: cards, never a horizontal
 * table).
 *
 * The order is the backend's — by name — so it does not reshuffle between
 * reloads and needs no sorting here. */
export function FirmsTable({ firms }: FirmsTableProps) {
  return (
    <Table.ScrollContainer minWidth={600}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Nombre</Table.Th>
            <Table.Th>Contacto</Table.Th>
            <Table.Th ta="right">Miembros</Table.Th>
            <Table.Th>Estado</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {firms.map((firm) => (
            <Table.Tr key={firm.id} opacity={firm.is_active ? 1 : 0.6}>
              <Table.Td>
                <Text fw={500}>{firm.name}</Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{firm.contact_email}</Text>
                {firm.phone && (
                  <Text size="sm" c="dimmed">
                    {firm.phone}
                  </Text>
                )}
              </Table.Td>
              <Table.Td ta="right">{firm.member_count}</Table.Td>
              <Table.Td>
                <FirmStatus isActive={firm.is_active} />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
