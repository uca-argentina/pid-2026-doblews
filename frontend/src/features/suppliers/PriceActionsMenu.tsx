import { ActionIcon, Menu } from "@mantine/core";
import { useCurrentFirm } from "../firms/firmContext";
import type { SupplierPriceOut } from "./types";

interface PriceActionsMenuProps {
  price: SupplierPriceOut;
  onEdit: (price: SupplierPriceOut) => void;
  onRemove: (price: SupplierPriceOut) => void;
}

/** What can be done to one row of a list, rendered by the table and the cards
 * alike. Asked of the permission (supplier.manage), never of the role. */
export function PriceActionsMenu({
  price,
  onEdit,
  onRemove,
}: PriceActionsMenuProps) {
  const { can } = useCurrentFirm();

  if (!can("supplier.manage")) {
    return null;
  }

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${price.resource.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => onEdit(price)}>Editar precio</Menu.Item>
        <Menu.Item color="red" onClick={() => onRemove(price)}>
          Quitar de la lista
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
