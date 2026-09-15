import { ActionIcon, Menu } from "@mantine/core";
import type { ResourceOut } from "./types";

interface MaterialActionsMenuProps {
  resource: ResourceOut;
  onEdit: (resource: ResourceOut) => void;
}

/** What support can do to one material, in one place: the table and the
 * card both render this, same reason FirmActionsMenu exists.
 *
 * No permission check inside, unlike FirmActionsMenu: this screen only
 * mounts behind RequirePlatformPermission code="catalog.manage" already, and
 * ADR-005 section 2 gives the catalogue exactly one write permission, not
 * one per action — there is no split to guard against here.
 *
 * "Dar de baja" joins this menu once DeactivateResourceModal exists. */
export function MaterialActionsMenu({
  resource,
  onEdit,
}: MaterialActionsMenuProps) {
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${resource.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={() => onEdit(resource)}>Editar</Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
