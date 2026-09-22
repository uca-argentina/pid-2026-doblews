import { Badge } from "@mantine/core";

/** Whether this person is still on the roster.
 *
 * Its own component because the table and the card both show it, and because
 * HU-2 asks the listing to include the people who left: without a visible
 * state an inactive row would read as an active one. */
export function MemberStatus({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge variant="light" color="obra">
      Activo
    </Badge>
  ) : (
    <Badge variant="light" color="gray">
      Inactivo
    </Badge>
  );
}
