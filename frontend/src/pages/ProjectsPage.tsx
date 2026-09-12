import { Stack, Text, Title } from "@mantine/core";
import { useCurrentFirm } from "../features/firms/firmContext";

/** Placeholder landing screen for HU-1: it exists so there is somewhere real
 * to redirect to and to prove the firm-scoped route works end to end. The
 * actual listing is HU-3.
 *
 * The firm comes already resolved from FirmLayout, which also answers a
 * foreign firm id with "not found" before this ever renders. */
export function ProjectsPage() {
  const { firm } = useCurrentFirm();

  return (
    <Stack gap="xs">
      <Title order={3}>{firm.name}</Title>
      <Text c="dimmed" size="sm">
        Rol: {firm.role.name}
      </Text>
      <Text mt="lg">Listado de obras — próximamente.</Text>
    </Stack>
  );
}
