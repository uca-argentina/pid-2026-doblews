import { Group, Progress, Text } from "@mantine/core";

/** A percentage with its label above it: how the dashboard and "Mis obras"
 * draw a work's real and planned progress. */
export function LabeledProgress({
  label,
  value,
  color,
  size = "lg",
}: {
  label: string;
  value: number;
  color: string;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <div>
      <Group justify="space-between" mb={4}>
        <Text size="sm">{label}</Text>
        <Text size="sm" fw={600}>
          {value}%
        </Text>
      </Group>
      <Progress value={value} color={color} size={size} aria-label={label} />
    </div>
  );
}
