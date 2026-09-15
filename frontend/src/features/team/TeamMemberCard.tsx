import { Card, Group, Stack, Text } from "@mantine/core";
import dayjs from "dayjs";
import { TeamActionsMenu } from "./TeamActionsMenu";
import { TeamMemberStatus } from "./TeamMemberStatus";
import type { ProjectMemberOut } from "./types";

interface TeamMemberCardProps {
  member: ProjectMemberOut;
  onChangeRole: (member: ProjectMemberOut) => void;
  onRemove: (member: ProjectMemberOut) => void;
}

/** One team row on a phone. Same data as a table row, stacked instead of side
 * by side, so 375px needs no horizontal scrolling.
 *
 * The email is truncated rather than wrapped: it is the longest field by far,
 * and letting it wrap pushes the rest of the card around. */
export function TeamMemberCard({
  member,
  onChangeRole,
  onRemove,
}: TeamMemberCardProps) {
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
            <TeamMemberStatus isActive={member.is_active} />
            <TeamActionsMenu
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
        <Text size="xs" c="dimmed">
          En el equipo desde {dayjs(member.joined_at).format("DD/MM/YYYY")}
        </Text>
      </Stack>
    </Card>
  );
}
