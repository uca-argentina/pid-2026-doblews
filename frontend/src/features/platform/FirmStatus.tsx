import { Badge } from "@mantine/core";

/** Whether a firm is open to its members or suspended by support.
 *
 * Its own component because the table and the card both show it, and because
 * the listing includes suspended firms on purpose: it is where support finds
 * one to reactivate. */
export function FirmStatus({ isActive }: { isActive: boolean }) {
  return isActive ? (
    <Badge variant="light" color="obra">
      Activo
    </Badge>
  ) : (
    <Badge variant="light" color="red">
      Suspendido
    </Badge>
  );
}
