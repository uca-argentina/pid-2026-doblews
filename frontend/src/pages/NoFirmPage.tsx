import { Stack, Text, Title } from "@mantine/core";

/** ADR-002 section 11.6: no firms is a valid state, not an error — it gets an
 * explanation, never an empty list or a failed request. */
export function NoFirmPage() {
  return (
    <Stack maw={480} mx="auto" gap="sm" ta="center">
      <Title order={3}>Todavía no pertenecés a ningún estudio</Title>
      <Text c="dimmed">
        Cuando un estudio te agregue a su padrón vas a poder ver sus obras desde acá.
      </Text>
    </Stack>
  );
}
