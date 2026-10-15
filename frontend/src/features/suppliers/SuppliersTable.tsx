import { Table, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { SupplierActionsMenu } from "./SupplierActionsMenu";
import type { SupplierOut } from "./types";

interface SuppliersTableProps {
  firmId: number;
  suppliers: SupplierOut[];
  onEdit: (supplier: SupplierOut) => void;
  onDeactivate: (supplier: SupplierOut) => void;
}

/** The firm's suppliers as a table, for screens wide enough to read one.
 * Mobile gets SupplierCard instead (frontend/CLAUDE.md: cards, never a
 * horizontal table). The order is the backend's, by name. */
export function SuppliersTable({
  firmId,
  suppliers,
  onEdit,
  onDeactivate,
}: SuppliersTableProps) {
  return (
    <Table.ScrollContainer minWidth={600}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Proveedor</Table.Th>
            <Table.Th>Contacto</Table.Th>
            <Table.Th>Email</Table.Th>
            <Table.Th ta="right">Materiales</Table.Th>
            {/* No heading: each ⋯ button names its supplier in its aria-label. */}
            <Table.Th w={60} />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {suppliers.map((supplier) => (
            <Table.Tr key={supplier.id}>
              <Table.Td>
                <Text
                  component={Link}
                  to={`/firms/${firmId}/suppliers/${supplier.id}`}
                  fw={500}
                  c="inherit"
                >
                  {supplier.name}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">
                  {[supplier.contact_name, supplier.phone]
                    .filter(Boolean)
                    .join(" · ") || "—"}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" c="dimmed">
                  {supplier.contact_email ?? "—"}
                </Text>
              </Table.Td>
              <Table.Td ta="right">{supplier.price_count}</Table.Td>
              <Table.Td>
                <SupplierActionsMenu
                  supplier={supplier}
                  onEdit={onEdit}
                  onDeactivate={onDeactivate}
                />
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
