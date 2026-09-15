import { Stack, Text, Title } from "@mantine/core";
import { AdminResourceBrowser } from "../features/catalog-admin/AdminResourceBrowser";

/** HU-8: every material of the system catalogue, administered by support.
 *
 * Its own route and nav entry, separate from "Recetas" — mirrors how HU-7
 * split "Estudios" and "Contraseñas" rather than one screen with a toggle. */
export function PlatformMaterialsPage() {
  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Materiales</Title>
        <Text c="dimmed" size="sm">
          El catálogo de materiales del sistema, igual para todos los estudios.
        </Text>
      </div>

      <AdminResourceBrowser />
    </Stack>
  );
}
