import { ActionIcon, Menu } from "@mantine/core";
import { useAuth } from "../auth/AuthContext";
import { canOnPlatform, PLATFORM_PERMISSIONS } from "./platformAccess";
import type { FirmAdminOut } from "./types";

interface FirmActionsMenuProps {
  firm: FirmAdminOut;
  onChangeStatus: (firm: FirmAdminOut) => void;
}

/** What support can do to one firm, in one place: the table and the cards both
 * render this, so an option never appears on one and not on the other — the
 * same reason MemberActionsMenu exists.
 *
 * A menu for a single option today on purpose. Editing a firm's data is the
 * next thing support will want (firm.edit is already seeded), and it lands
 * here as a second item rather than as a second button squeezed into a card. */
export function FirmActionsMenu({
  firm,
  onChangeStatus,
}: FirmActionsMenuProps) {
  const { account } = useAuth();

  // No empty ⋯ button: a menu that opens onto nothing reads as a bug.
  if (!canOnPlatform(account, PLATFORM_PERMISSIONS.suspendFirm)) {
    return null;
  }

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${firm.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item
          color={firm.is_active ? "red" : undefined}
          onClick={() => onChangeStatus(firm)}
        >
          {firm.is_active ? "Suspender" : "Reactivar"}
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}
