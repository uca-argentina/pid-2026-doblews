import type { ReactNode } from "react";
import { AppShell, Burger, Button, Group, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

interface AppShellLayoutProps {
  /** Renders the sidebar. Receives close() so a link can fold the mobile
   * drawer after navigating. Without it there is no sidebar and no burger,
   * which is what the screens outside a firm (picker, no-firm) want. */
  navbar?: (close: () => void) => ReactNode;
  /** What goes in the main area. Defaults to the matched child route; a layout
   * passes something else to show a loader or an error in its place. */
  children?: ReactNode;
}

/** Shell for every authenticated screen. Exists mainly to satisfy the HU-1
 * criterion that a logout button is visible everywhere once you are logged
 * in, not only on the projects screen. */
export function AppShellLayout({ navbar, children }: AppShellLayoutProps) {
  const { account, logout } = useAuth();
  // Only the mobile drawer opens and closes. From "sm" up the sidebar is
  // always visible, so there is nothing to toggle there.
  const [opened, { toggle, close }] = useDisclosure();

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={
        navbar
          ? { width: 240, breakpoint: "sm", collapsed: { mobile: !opened } }
          : undefined
      }
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            {navbar && (
              <Burger
                opened={opened}
                onClick={toggle}
                hiddenFrom="sm"
                size="sm"
                aria-label={opened ? "Cerrar menú" : "Abrir menú"}
              />
            )}
            <Text fw={600}>Warchitecture</Text>
          </Group>
          <Group gap="sm" wrap="nowrap">
            {account && (
              <Text size="sm" c="dimmed" truncate visibleFrom="xs">
                {account.name}
              </Text>
            )}
            <Button variant="subtle" size="sm" onClick={logout}>
              Cerrar sesión
            </Button>
          </Group>
        </Group>
      </AppShell.Header>

      {navbar && <AppShell.Navbar p="md">{navbar(close)}</AppShell.Navbar>}

      <AppShell.Main>{children ?? <Outlet />}</AppShell.Main>
    </AppShell>
  );
}
