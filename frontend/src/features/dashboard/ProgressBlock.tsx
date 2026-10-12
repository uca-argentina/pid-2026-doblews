import { Group, Progress, SimpleGrid, Stack, Text } from "@mantine/core";
import { formatDate } from "../projects/projectFields";
import { DashboardBlock, Figure, MissingData } from "./DashboardBlock";
import type { ProgressBlockOut } from "./types";

/** Avance planificado vs. real de la obra entera (HU-19), taken as it is from
 * HU-16: each task weighs its duration, against the planning fixed on the
 * Avance tab. Below it, when the work is planned to end against when it was
 * planned to end then.
 *
 * The deviation is a number and not a verdict, as on the Avance tab (ADR-009
 * section 13): the work is not called late because its progress trails an
 * even pace. What does flag it is the count of tasks whose fixed end has
 * passed unfinished — the same "atrasada" that tab shows. */
export function ProgressBlock({
  block,
  planningPath,
  progressPath,
}: {
  block: ProgressBlockOut;
  planningPath: string;
  progressPath: string;
}) {
  return (
    <DashboardBlock title="Avance planificado vs. real">
      <Content
        block={block}
        planningPath={planningPath}
        progressPath={progressPath}
      />
    </DashboardBlock>
  );
}

function Content({
  block,
  planningPath,
  progressPath,
}: {
  block: ProgressBlockOut;
  planningPath: string;
  progressPath: string;
}) {
  if (!block.has_tasks) {
    return (
      <MissingData to={planningPath} linkLabel="Ir a Planificación">
        La obra no tiene tareas. Cargalas en la planificación para medir su
        avance.
      </MissingData>
    );
  }
  if (block.project_start_date === null) {
    return (
      <MissingData to={planningPath} linkLabel="Ir a Planificación">
        Falta la fecha de inicio de la obra: sin ella no hay fechas previstas
        contra las que comparar.
      </MissingData>
    );
  }

  const { progress } = block;

  return (
    <Stack gap="md">
      {progress === null ? (
        <MissingData to={progressPath} linkLabel="Ir a Avance">
          Todavía no hay una planificación fijada. Fijala en Avance para
          comparar lo real contra lo planificado.
        </MissingData>
      ) : (
        <Stack gap="xs">
          <Bar label="Real" value={progress.actual_percent} color="obra" />
          <Bar
            label="Planificado a hoy"
            value={progress.planned_percent}
            color="gray"
          />
          <Group gap="md" align="baseline" wrap="wrap">
            <Text fw={700}>
              Desvío: {progress.gap > 0 ? "+" : ""}
              {progress.gap} {Math.abs(progress.gap) === 1 ? "punto" : "puntos"}
            </Text>
            <Text
              size="sm"
              c={block.overdue_tasks > 0 ? "red" : "dimmed"}
              fw={block.overdue_tasks > 0 ? 600 : undefined}
            >
              {block.overdue_tasks === 0
                ? "Ninguna tarea atrasada"
                : block.overdue_tasks === 1
                  ? "1 tarea atrasada"
                  : `${block.overdue_tasks} tareas atrasadas`}
            </Text>
          </Group>
        </Stack>
      )}

      <SimpleGrid cols={2} spacing="md">
        <Figure label="Fin previsto">
          {formatDate(block.planned_end_date)}
        </Figure>
        <Figure label="Fin planificado" hint={delayText(block.end_delay_days)}>
          {formatDate(block.baseline_end_date)}
        </Figure>
      </SimpleGrid>
    </Stack>
  );
}

function Bar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div>
      <Group justify="space-between" mb={4}>
        <Text size="sm">{label}</Text>
        <Text size="sm" fw={600}>
          {value}%
        </Text>
      </Group>
      <Progress value={value} color={color} size="lg" aria-label={label} />
    </div>
  );
}

/** How far the planned end has moved from the fixed one, in working days. */
function delayText(days: number | null): string | undefined {
  if (days === null) return undefined;
  if (days === 0) return "Sin atraso";
  const amount =
    Math.abs(days) === 1 ? "1 día hábil" : `${Math.abs(days)} días hábiles`;
  return days > 0 ? `${amount} de atraso` : `${amount} de adelanto`;
}
