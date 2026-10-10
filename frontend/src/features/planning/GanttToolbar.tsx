import { Box, Button, Group, SegmentedControl, Text } from "@mantine/core";
import type { GanttScale } from "./ganttScale";
import { STATUS_COLORS, STATUS_LABELS } from "./taskStatus";
import type { TaskStatus } from "./types";

interface GanttToolbarProps {
  scale: GanttScale;
  onScaleChange: (scale: GanttScale) => void;
  /** Move the window of time one screen back or forward, or onto today. */
  onPrevious: () => void;
  onToday: () => void;
  onNext: () => void;
}

const SCALES: { value: GanttScale; label: string }[] = [
  { value: "day", label: "Días" },
  { value: "week", label: "Semanas" },
  { value: "month", label: "Meses" },
];

const STATUSES: TaskStatus[] = ["pending", "in_progress", "paused", "finished"];

/** What sits above the Gantt: how far it is zoomed, where in time it is
 * looking, and what its colours mean. */
export function GanttToolbar({
  scale,
  onScaleChange,
  onPrevious,
  onToday,
  onNext,
}: GanttToolbarProps) {
  return (
    <Group justify="space-between" gap="sm">
      <Group gap="sm">
        <SegmentedControl
          size="xs"
          aria-label="Escala de tiempo"
          value={scale}
          onChange={(value) => onScaleChange(value as GanttScale)}
          data={SCALES}
        />
        <Button.Group>
          <Button
            size="xs"
            variant="default"
            onClick={onPrevious}
            aria-label="Ver antes"
          >
            ‹
          </Button>
          <Button size="xs" variant="default" onClick={onToday}>
            Hoy
          </Button>
          <Button
            size="xs"
            variant="default"
            onClick={onNext}
            aria-label="Ver después"
          >
            ›
          </Button>
        </Button.Group>
      </Group>

      <Group gap="md">
        {STATUSES.map((status) => (
          <LegendItem
            key={status}
            label={STATUS_LABELS[status]}
            color={STATUS_COLORS[status]}
            // A pending task has nothing behind it, so its bar is never
            // solid: the sample is drawn the way the bar is.
            solid={status !== "pending"}
          />
        ))}
        <LegendItem label="Crítica" color="red" solid={false} />
      </Group>
    </Group>
  );
}

function LegendItem({
  label,
  color,
  solid,
}: {
  label: string;
  color: string;
  solid: boolean;
}) {
  return (
    <Group gap={6} wrap="nowrap">
      <Box
        w={14}
        h={10}
        bg={`var(--mantine-color-${color}-${solid ? "filled" : "light"})`}
        style={{
          border: `1px solid var(--mantine-color-${color}-filled)`,
          borderRadius: 2,
        }}
      />
      <Text size="xs" c="dimmed">
        {label}
      </Text>
    </Group>
  );
}
