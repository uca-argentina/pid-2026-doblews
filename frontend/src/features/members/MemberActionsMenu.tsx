import { ActionIcon, Menu } from "@mantine/core";
import { useAuth } from "../auth/AuthContext";
import { useCurrentFirm } from "../firms/firmContext";
import type { MemberOut } from "./types";

interface MemberActionsMenuProps {
  member: MemberOut;
  onChangeRole: (member: MemberOut) => void;
  onRemove: (member: MemberOut) => void;
}

/** What can be done to one person, in one place: the table and the cards both
 * render this, so an option never appears on one and not on the other.
 *
 * Two different questions decide what it offers, and they are not the same
 * kind of question:
 *
 * - what the *caller* may do is asked of the permissions (member.edit_role,
 *   member.remove), never of their role;
 * - what may be done to *this member* is a domain rule: the backend always
 *   refuses editing or removing yourself and the owner (ADR-002 sections 11.1
 *   and 11.5), so offering it would only produce a 409 nobody can act on.
 *
 * Reading member.role.code here is that second question, the same distinction
 * services/roster.py makes on the backend. */
export function MemberActionsMenu({
  member,
  onChangeRole,
  onRemove,
}: MemberActionsMenuProps) {
  const { account } = useAuth();
  const { can } = useCurrentFirm();

  // Someone who left has a different set of actions — bringing them back —
  // which arrives with the reinstate step.
  if (!member.is_active) {
    return null;
  }

  const isSelf = account?.id === member.account_id;
  const isOwner = member.role.code === "owner";
  const editable = can("member.edit_role") && !isSelf && !isOwner;
  const removable = can("member.remove") && !isSelf && !isOwner;

  // No empty ⋯ button: a menu that opens onto nothing reads as a bug.
  if (!editable && !removable) {
    return null;
  }

  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon
          variant="subtle"
          color="gray"
          aria-label={`Acciones de ${member.name}`}
        >
          ⋯
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {editable && (
          <Menu.Item onClick={() => onChangeRole(member)}>
            Cambiar rol
          </Menu.Item>
        )}
        {removable && (
          <Menu.Item color="red" onClick={() => onRemove(member)}>
            Dar de baja
          </Menu.Item>
        )}
      </Menu.Dropdown>
    </Menu>
  );
}
