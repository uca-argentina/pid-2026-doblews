import { Badge } from "@mantine/core";

/** Whether this person is still on the firm's roster.
 *
 * Its own component because the table and the card both show it, and worded
 * differently from MemberStatus in the roster on purpose. There the badge is
 * about the roster itself, so "Inactivo" is unambiguous. Here the row is an
 * assignment to a work, and "Inactivo" would read as "inactive on this
 * project" — which is not a state that exists. What actually happened is that
 * they left the studio, so their seat grants nothing until they are back
 * (ADR-002 section 11.3). */
export function TeamMemberStatus({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge variant="light" color="obra">
      Activo
    </Badge>
  ) : (
    <Badge variant="light" color="gray">
      Fuera del estudio
    </Badge>
  );
}
