import type { ReactNode } from "react";
import { Group, Stack, Text } from "@mantine/core";
import { EMPTY, formatDate } from "../projects/projectFields";
import type { PlanningOut } from "./types";

interface ProgressSummaryProps {
  planning: PlanningOut;
  /** How many tasks are past the end fixed for them and not finished. */
  overdueCount: number;
}

/** How the whole work is doing against its fixed planning (HU-16): the two
 * percentages and the two ends, side by side, in the same shape as the
 * planning's own dates.
 *
 * Numbers and no verdict. The work is not labelled late or on time: what
 * says so is the line below, which counts the tasks whose fixed end has
 * passed. The percentages weigh each task by its duration (ADR-009 13).
 *
 * Rendered only once a planning is fixed. `progress` is still null when none
 * of the tasks that were there then is left, and then the numbers are dashes
 * and the line asks to fix it again. */
export function ProgressSummary({
  planning,
  overdueCount,
}: ProgressSummaryProps) {
  const { progress } = planning;

  return (
    <Stack gap="xs">
      <Group gap="xl" px={{ sm: "sm" }}>
        <Stat label="Avance real" strong>
          {progress ? `${progress.actual_percent}%` : EMPTY}
        </Stat>
        <Stat label="Planificado a hoy">
          {progress ? `${progress.planned_percent}%` : EMPTY}
        </Stat>
        <Stat label="Fin previsto">
          {formatDate(planning.planned_end_date)}
        </Stat>
        <Stat label="Fin planificado">
          {formatDate(planning.baseline_end_date)}
        </Stat>
      </Group>

      <Text size="sm" c="dimmed" px={{ sm: "sm" }}>
        Planificación fijada el {formatDate(planning.baseline_set_on)}
        {progress === null
          ? ". Ninguna de las tareas de entonces sigue en la obra: volvé a fijarla para comparar las actuales."
          : overdueCount > 0 &&
            ` · ${
              overdueCount === 1
                ? "1 tarea atrasada"
                : `${overdueCount} tareas atrasadas`
            }`}
      </Text>
    </Stack>
  );
}

function Stat({
  label,
  strong = false,
  children,
}: {
  label: string;
  strong?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={strong ? 700 : 500}>{children}</Text>
    </div>
  );
}
