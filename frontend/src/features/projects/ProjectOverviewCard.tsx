import { Anchor, Card, Divider, Group, Stack, Text } from "@mantine/core";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { LabeledProgress } from "../../components/LabeledProgress";
import { formatMoney } from "../../lib/format";
import { formatDate } from "./projectFields";
import type { ProjectOverviewOut } from "./types";

/** One work of "Mis obras" (HU-26): how it is going, when it should end and
 * the last budget the studio saved, each read from the section it summarises.
 *
 * The name leads to the work. The version is a link of its own, straight to
 * that budget, so the card is not one big link with another inside it. */
export function ProjectOverviewCard({
  work,
  workPath,
}: {
  work: ProjectOverviewOut;
  workPath: string;
}) {
  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap="sm">
        <div>
          <Anchor component={Link} to={workPath} fw={600} size="lg">
            {work.name}
          </Anchor>
          {work.address && (
            <Text size="sm" c="dimmed">
              {work.address}
            </Text>
          )}
        </div>

        <WorkProgress work={work} />

        <div>
          <Group justify="space-between" gap="xs" wrap="wrap">
            <Text size="sm" c="dimmed">
              Fin previsto
            </Text>
            <Text size="sm" fw={600}>
              {formatDate(work.planned_end_date)}
            </Text>
          </Group>
          {work.baseline_end_date && (
            <Text size="xs" c="dimmed">
              Planificado para el {formatDate(work.baseline_end_date)}
            </Text>
          )}
        </div>

        <Divider />

        <LatestVersion work={work} workPath={workPath} />
      </Stack>
    </Card>
  );
}

/** Real against planned, or why there is nothing to compare yet. The same
 * deviation in points as the Avance tab, and no verdict on it. */
function WorkProgress({ work }: { work: ProjectOverviewOut }) {
  if (!work.has_tasks) {
    return (
      <Text size="sm" c="dimmed">
        Sin planificación todavía.
      </Text>
    );
  }
  if (work.progress === null) {
    return (
      <Text size="sm" c="dimmed">
        El estudio todavía no fijó la planificación, así que no hay avance
        planificado contra el que comparar.
      </Text>
    );
  }
  const { progress } = work;
  return (
    <Stack gap={6}>
      <LabeledProgress
        label="Avance real"
        value={progress.actual_percent}
        color="obra"
        size="md"
      />
      <LabeledProgress
        label="Planificado a hoy"
        value={progress.planned_percent}
        color="gray"
        size="md"
      />
      <Text size="xs" c="dimmed">
        Desvío: {progress.gap > 0 ? "+" : ""}
        {progress.gap} {Math.abs(progress.gap) === 1 ? "punto" : "puntos"}
      </Text>
    </Stack>
  );
}

function LatestVersion({
  work,
  workPath,
}: {
  work: ProjectOverviewOut;
  workPath: string;
}) {
  const version = work.latest_version;
  if (version === null) {
    return (
      <Text size="sm" c="dimmed">
        Sin presupuesto presentado todavía.
      </Text>
    );
  }
  return (
    <Stack gap={2}>
      <Text size="sm" c="dimmed">
        Último presupuesto
      </Text>
      <Group justify="space-between" gap="xs" wrap="wrap">
        <Anchor
          component={Link}
          to={`${workPath}/budget/versions/${version.id}`}
          size="sm"
        >
          v{version.version_number} ·{" "}
          {dayjs(version.created_at).format("DD/MM/YYYY")}
        </Anchor>
        <Text fw={700}>{formatMoney(version.total, version.currency)}</Text>
      </Group>
    </Stack>
  );
}
