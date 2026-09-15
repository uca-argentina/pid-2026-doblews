import { Stack, Text, Title } from "@mantine/core";
import { AdminRecipeBrowser } from "../features/catalog-admin/AdminRecipeBrowser";

/** HU-8: every recipe of the system catalogue, administered by support. */
export function PlatformRecipesPage() {
  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Recetas</Title>
        <Text c="dimmed" size="sm">
          Las recetas del catálogo del sistema, con lo que lleva cada una.
        </Text>
      </div>

      <AdminRecipeBrowser />
    </Stack>
  );
}
