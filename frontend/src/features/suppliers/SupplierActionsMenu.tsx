import { ActionIcon, Menu } from "@mantine/core";
import { useCurrentFirm } from "../firms/firmContext";
import type { SupplierOut } from "./types";

interface SupplierActionsMenuProps {
  supplier: SupplierOut;
  onEdit: (supplier: SupplierOut) => void;
  onDeactivate: (supplier: SupplierOut) => void;
}

/** What can be done to one supplier, in one place: the table, the cards and the
 * supplier's own screen all render this, so an option never appears on one and
 * not on another. What the caller may do is asked of the permission
 * (supplier.manage), never of their role. */
export function SupplierActionsMenu({
  supplier,
  onEdit,
  onDeactivate,
}: SupplierActionsMenuProps) {
  const { can } = useCurrentFirm();

  // No empty ⋯ button: a menu that opens onto nothing reads as a bug.
  if (!can("supplier.manage")) {
    return null;
  }

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${supplier.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => onEdit(supplier)}>Editar</Menu.Item>
        <Menu.Item color="red" onClick={() => onDeactivate(supplier)}>
          Dar de baja
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
