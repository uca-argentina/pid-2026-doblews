import { ActionIcon, Menu } from "@mantine/core";
import { useCurrentProject } from "../projects/projectContext";
import { LEAD, type ProjectMemberOut } from "./types";

interface TeamActionsMenuProps {
  member: ProjectMemberOut;
  onChangeRole: (member: ProjectMemberOut) => void;
  onRemove: (member: ProjectMemberOut) => void;
}

interface TeamAction {
  label: string;
  color?: string;
  onClick: () => void;
}

/** What can be done to one person on this work, in one place: the table and
 * the cards both render this, so an option never appears on one and not on
 * the other.
 *
 * Two different questions decide what it offers, and they are not the same
 * kind of question — the same split MemberActionsMenu makes in the roster:
 *
 * - what the *caller* may do is asked of the permissions
 *   (project.member.manage), never of their role in the work;
 * - what may be done to *this member* is a domain rule. The backend refuses
 *   both moving the lead off their role and removing them, because the work
 *   would be left with nobody responsible; the way to replace them is to give
 *   lead to somebody else, which transfers it. Offering either would only
 *   produce a 409 nobody can act on.
 *
 * Someone who left the studio can only be taken off. Their seat is inert and
 * changing its role would be refused, since a role granted to a person the
 * firm no longer has is worth nothing — but tidying the team up is fair. */
export function TeamActionsMenu({
  member,
  onChangeRole,
  onRemove,
}: TeamActionsMenuProps) {
  const { can } = useCurrentProject();

  if (!can("project.member.manage") || member.role.code === LEAD) {
    return null;
  }

  const actions: TeamAction[] = [];
  if (member.is_active) {
    actions.push({ label: "Cambiar rol", onClick: () => onChangeRole(member) });
  }
  actions.push({
    label: "Quitar del equipo",
    color: "red",
    onClick: () => onRemove(member),
  });

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
