import { Card, Group, Stack, Text } from "@mantine/core";
import { MemberActionsMenu } from "./MemberActionsMenu";
import { MemberStatus } from "./MemberStatus";
import type { MemberOut } from "./types";

interface MemberCardProps {
  member: MemberOut;
  onChangeRole: (member: MemberOut) => void;
  onRemove: (member: MemberOut) => void;
}

/** One roster row on a phone. Same data as a table row, stacked instead of
 * side by side, so 375px needs no horizontal scrolling.
 *
 * The email is truncated rather than wrapped: it is the longest field by far,
 * and letting it wrap pushes the rest of the card around. */
export function MemberCard({
  member,
  onChangeRole,
  onRemove,
}: MemberCardProps) {
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
          <Group gap="xs" wrap="nowrap">
            <MemberStatus isActive={member.is_active} />
            <MemberActionsMenu
              member={member}
              onChangeRole={onChangeRole}
              onRemove={onRemove}
            />
          </Group>
        </Group>
        <Text size="sm" c="dimmed" truncate>
          {member.email}
        </Text>
        <Text size="sm">{member.role.name}</Text>
      </Stack>
    </Card>
  );
}
