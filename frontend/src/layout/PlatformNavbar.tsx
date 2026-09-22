import { NavLink, Stack, Text } from "@mantine/core";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import {
  canOnPlatform,
  PLATFORM_PERMISSIONS,
} from "../features/platform/platformAccess";

interface PlatformNavbarProps {
  /** Called after a link is followed, so the mobile drawer folds away. */
  onNavigate: () => void;
}

/** The support sections. Like FirmNavbar, a section appears only when the
 * caller holds the permission its screen checks, so the link and the door
 * always agree. */
export function PlatformNavbar({ onNavigate }: PlatformNavbarProps) {
  const { account } = useAuth();
  const { pathname } = useLocation();

  const sections = [
    {
      to: "/platform/firms",
      label: "Estudios",
      visible: canOnPlatform(account, PLATFORM_PERMISSIONS.viewFirms),
    },
    {
      to: "/platform/password-reset",
      label: "Contraseñas",
      visible: canOnPlatform(account, PLATFORM_PERMISSIONS.resetPassword),
    },
    {
      to: "/platform/catalog/materials",
      label: "Materiales",
      visible: canOnPlatform(account, PLATFORM_PERMISSIONS.manageCatalog),
    },
    {
      to: "/platform/catalog/recipes",
      label: "Recetas",
      visible: canOnPlatform(account, PLATFORM_PERMISSIONS.manageCatalog),
    },
  ];

  return (
    <Stack gap="xs">
      <div>
        <Text fw={600}>Soporte</Text>
        <Text size="sm" c="dimmed">
          Administración de la plataforma
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
              active={pathname.startsWith(section.to)}
              onClick={onNavigate}
            />
          ))}
      </Stack>
    </Stack>
  );
}
