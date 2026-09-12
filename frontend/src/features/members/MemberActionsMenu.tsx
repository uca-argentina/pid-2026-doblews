import { ActionIcon, Menu } from "@mantine/core";
import { useAuth } from "../auth/AuthContext";
import { useCurrentFirm } from "../firms/firmContext";
import type { MemberOut } from "./types";

interface MemberActionsMenuProps {
  member: MemberOut;
  onChangeRole: (member: MemberOut) => void;
  onRemove: (member: MemberOut) => void;
  onReinstate: (member: MemberOut) => void;
}

interface MemberAction {
  label: string;
  color?: string;
  onClick: () => void;
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
  onReinstate,
}: MemberActionsMenuProps) {
  const { account } = useAuth();
  const { can } = useCurrentFirm();

  const isSelf = account?.id === member.account_id;
  const isOwner = member.role.code === "owner";
  const actions: MemberAction[] = [];

  if (member.is_active) {
    if (can("member.edit_role") && !isSelf && !isOwner) {
      actions.push({
        label: "Cambiar rol",
        onClick: () => onChangeRole(member),
      });
    }
    if (can("member.remove") && !isSelf && !isOwner) {
      actions.push({
        label: "Dar de baja",
        color: "red",
        onClick: () => onRemove(member),
      });
    }
  } else if (can("member.add")) {
    // Bringing someone back is an add: same endpoint, same permission. The
    // self and owner checks do not apply, because neither can be inactive.
    actions.push({ label: "Reincorporar", onClick: () => onReinstate(member) });
  }

  // No empty ⋯ button: a menu that opens onto nothing reads as a bug.
  if (actions.length === 0) {
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
        {actions.map((action) => (
          <Menu.Item
            key={action.label}
            color={action.color}
            onClick={action.onClick}
          >
            {action.label}
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  );
}
