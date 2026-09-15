import { Card, Group, Stack, Text } from "@mantine/core";
import { FirmStatus } from "./FirmStatus";
import type { FirmAdminOut } from "./types";

interface FirmCardProps {
  firm: FirmAdminOut;
}

/** One firm on a phone. Same data as a table row, stacked instead of side by
 * side, so 375px needs no horizontal scrolling. The email is truncated rather
 * than wrapped, as in MemberCard: it is the longest field by far. */
export function FirmCard({ firm }: FirmCardProps) {
  const members = firm.member_count === 1 ? "miembro" : "miembros";

  return (
    <Card
      withBorder
      padding="md"
      radius="md"
      opacity={firm.is_active ? 1 : 0.6}
    >
      <Stack gap={4}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600} truncate>
            {firm.name}
          </Text>
          <FirmStatus isActive={firm.is_active} />
        </Group>
        <Text size="sm" c="dimmed" truncate>
          {firm.contact_email}
          {firm.phone && ` · ${firm.phone}`}
        </Text>
        <Text size="sm">
          {firm.member_count} {members}
        </Text>
      </Stack>
    </Card>
  );
}
