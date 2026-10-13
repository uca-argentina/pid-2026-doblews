import { NavLink, Stack, Text } from "@mantine/core";
import { Link, useLocation } from "react-router-dom";
import { useCurrentFirm } from "../features/firms/firmContext";

interface FirmNavbarProps {
  /** Called after a link is followed, so the mobile drawer folds away. */
  onNavigate: () => void;
}

/** The sections of the active firm. A section appears only when the caller
 * holds the permission it demands: the roster is gated on member.add, the same
 * permission its screen checks, so the link and the door always agree. */
export function FirmNavbar({ onNavigate }: FirmNavbarProps) {
  const { firm, can } = useCurrentFirm();
  const { pathname } = useLocation();

  const base = `/firms/${firm.id}`;
  const sections = [
    { to: `${base}/projects`, label: "Obras", visible: true },
    {
      to: `${base}/catalog`,
      label: "Catálogo",
      visible: can("catalog.view"),
    },
    {
      to: `${base}/suppliers`,
      label: "Proveedores",
      visible: can("supplier.view"),
    },
    { to: `${base}/members`, label: "Padrón", visible: can("member.add") },
  ];

  return (
    <Stack gap="xs">
      <div>
        <Text fw={600} truncate>
          {firm.name}
        </Text>
        <Text size="sm" c="dimmed">
          {firm.role.name}
        </Text>
      </div>

      <Stack gap={4}>
        {sections
          .filter((section) => section.visible)
          .map((section) => (
            <NavLink
              key={section.to}
              component={Link}
              to={section.to}
              label={section.label}
              // startsWith and not equality, so a screen nested under a
              // section later still lights its section up.
              active={pathname.startsWith(section.to)}
              onClick={onNavigate}
            />
          ))}
      </Stack>
    </Stack>
  );
}
