import { Card, Group, Stack, Text } from "@mantine/core";
import { MemberStatus } from "./MemberStatus";
import type { MemberOut } from "./types";

/** One roster row on a phone. Same data as a table row, stacked instead of
 * side by side, so 375px needs no horizontal scrolling.
 *
 * The email is truncated rather than wrapped: it is the longest field by far,
 * and letting it wrap pushes the rest of the card around. */
export function MemberCard({ member }: { member: MemberOut }) {
  return (
    <Card
      withBorder
      padding="md"
      radius="md"
      opacity={member.is_active ? 1 : 0.6}
    >
      <Stack gap={4}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600} truncate>
            {member.name}
          </Text>
          <MemberStatus isActive={member.is_active} />
        </Group>
        <Text size="sm" c="dimmed" truncate>
          {member.email}
        </Text>
        <Text size="sm">{member.role.name}</Text>
      </Stack>
    </Card>
  );
}
