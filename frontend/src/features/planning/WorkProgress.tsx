import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Progress,
  Stack,
  Text,
} from "@mantine/core";
import { formatDate } from "../projects/projectFields";
import { STANDING_COLORS, STANDING_LABELS, formatGap } from "./progress";
import type { PlanningOut } from "./types";

interface WorkProgressProps {
  planning: PlanningOut;
  /** Opens the confirmation that fixes the planning, for those who may manage
   * it. Omitted for everyone else, who only read. */
  onFix?: () => void;
}

/** The progress of the whole work against its fixed planning (HU-16), and the
 * way to fix it.
 *
 * Three states. With no planning fixed there is nothing to compare, so this
 * is the request for one. With one fixed, the two numbers and whether the
 * work is behind, on track or ahead. And between the two, the odd case of a
 * planning fixed whose tasks were all removed since.
 *
 * The page renders this only for a work that can be fixed — one with a start
 * date and at least one task: before that, the notices above ask for those. */
export function WorkProgress({ planning, onFix }: WorkProgressProps) {
  if (planning.baseline_set_on === null) {
    return (
      <Alert color="blue" variant="light" title="Falta fijar la planificación">
        <Stack gap="sm" align="flex-start">
          <Text size="sm">
            Las fechas previstas se corren solas con cada atraso, así que el
            avance se compara contra una copia de ellas.
            {onFix
              ? " Fijala cuando la planificación esté lista para ver si la obra viene en fecha."
              : " Cuando se fije, vas a ver acá si la obra viene en fecha."}
          </Text>
          {onFix && (
            <Button size="xs" onClick={onFix}>
              Fijar planificación
            </Button>
          )}
        </Stack>
      </Alert>
    );
  }

  const { progress } = planning;

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="sm">
        <Group justify="space-between" align="center">
          <Text fw={600}>Avance de la obra</Text>
          {progress && (
            <Badge variant="light" color={STANDING_COLORS[progress.standing]}>
              {STANDING_LABELS[progress.standing]}
              {progress.gap !== 0 && ` ${formatGap(progress.gap)}`}
            </Badge>
          )}
        </Group>

        {progress ? (
          <Stack gap="xs">
            <Bar label="Real" percent={progress.actual_percent} color="obra" />
            <Bar
              label="Planificado"
              percent={progress.planned_percent}
              color="gray"
            />
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            Ninguna de las tareas que estaban al fijar la planificación sigue en
            la obra. Volvé a fijarla para comparar las actuales.
          </Text>
        )}

        <Group justify="space-between" align="center" gap="sm">
          <Text size="xs" c="dimmed">
            Planificación fijada el {formatDate(planning.baseline_set_on)}. Cada
            tarea pesa por su duración.
          </Text>
          {onFix && (
            <Button size="xs" variant="default" onClick={onFix}>
              Volver a fijar
            </Button>
          )}
        </Group>
      </Stack>
    </Card>
  );
}

/** One of the two numbers, as a bar with its label and its value. The label
 * and the value have a fixed width so the two bars line up. */
function Bar({
  label,
  percent,
  color,
}: {
  label: string;
  percent: number;
  color: string;
}) {
  return (
    <Group gap="sm" wrap="nowrap">
      <Text size="sm" w={84}>
        {label}
      </Text>
      <Progress
        value={percent}
        color={color}
        size="lg"
        style={{ flex: 1 }}
        aria-label={`Avance ${label.toLowerCase()} de la obra`}
      />
      <Text size="sm" fw={600} w={44} ta="right">
        {percent}%
      </Text>
    </Group>
  );
}
