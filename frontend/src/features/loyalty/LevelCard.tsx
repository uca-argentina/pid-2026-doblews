import { Card, Group, Progress, Stack, Text } from "@mantine/core";
import {
  LEVEL_COLORS,
  LEVEL_LABELS,
  levelProgress,
  nextLevelText,
} from "./loyaltyDisplay";
import type { LevelOut } from "./types";

interface LevelCardProps {
  level: LevelOut;
  /** What this level is about: the firm, or the firm with one supplier. */
  title: string;
  description?: string;
}

/** A level with its points and its bar (HU-24).
 *
 * The same card on the firm's own section and on each supplier's, so the two
 * never drift apart: both are a total of points, read the same way. */
export function LevelCard({ level, title, description }: LevelCardProps) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" align="baseline" wrap="wrap" gap="xs">
          <Text size="sm" c="dimmed">
            {title}
          </Text>
          <Text size="sm" c="dimmed">
            {level.points} {level.points === 1 ? "punto" : "puntos"}
          </Text>
        </Group>

        <Text fw={700} size="xl" c={LEVEL_COLORS[level.level]}>
          {LEVEL_LABELS[level.level]}
        </Text>

        <Progress
          value={levelProgress(level)}
          color={LEVEL_COLORS[level.level]}
          size="lg"
          radius="sm"
          aria-label={`Progreso hacia el próximo nivel: ${nextLevelText(level)}`}
        />

        <Text size="sm" c="dimmed">
          {nextLevelText(level)}
        </Text>

        {description && (
          <Text size="xs" c="dimmed">
            {description}
          </Text>
        )}
      </Stack>
    </Card>
  );
}
