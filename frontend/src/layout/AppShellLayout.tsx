import { AppShell, Button, Group, Text } from "@mantine/core";
import { Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

/** Shell for every authenticated screen. Exists mainly to satisfy the HU-1
 * criterion that a logout button is visible everywhere once you are logged
 * in, not only on the projects screen. */
export function AppShellLayout() {
  const { account, logout } = useAuth();

  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Text fw={600}>Warchitecture</Text>
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

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
