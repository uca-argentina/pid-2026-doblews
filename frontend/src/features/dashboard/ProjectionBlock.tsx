import { BarChart } from "@mantine/charts";
import { Divider, Group, Stack, Text } from "@mantine/core";
import dayjs from "dayjs";
import "dayjs/locale/es";
import { formatMoney } from "../../lib/format";
import { DashboardBlock, MissingData } from "./DashboardBlock";
import type { ProjectionOut } from "./types";

/** "2026-10-01" → "oct 2026". */
function monthLabel(month: string): string {
  return dayjs(month).locale("es").format("MMM YYYY");
}

/** Proyección mensual de gastos (HU-19, D-18): what is expected to be spent in
 * each month of the work, in a chart and with its amounts.
 *
 * Each task spends its cost evenly over its working days, on its planned
 * dates — or its actual ones, once they happened. The months already gone by
 * are a series of their own, dimmed, so the chart still adds up to everything
 * planned. What the take-off has outside every task is said underneath and
 * never spread: nobody planned when it is spent. */
export function ProjectionBlock({
  projection,
  currency,
  planningPath,
}: {
  projection: ProjectionOut;
  currency: string;
  planningPath: string;
}) {
  const money = (amount: string | number) =>
    formatMoney(String(amount), currency);
  const hasSpending = Number(projection.projected_total) > 0;

  return (
    <DashboardBlock title="Proyección mensual de gastos">
      {projection.months.length === 0 ? (
        <MissingData to={planningPath} linkLabel="Ir a Planificación">
          No hay nada que proyectar todavía: la obra necesita fecha de inicio y
          tareas, con líneas del cómputo asignadas.
        </MissingData>
      ) : !hasSpending ? (
        <MissingData to={planningPath} linkLabel="Ir a Planificación">
          Ninguna tarea tiene costo. Asigná a cada tarea sus líneas del cómputo
          para ver cuándo se gasta.
        </MissingData>
      ) : (
        <Stack gap="md">
          <BarChart
            h={260}
            data={projection.months.map((month) => ({
              month: monthLabel(month.month),
              Transcurrido: month.is_past ? Number(month.amount) : 0,
              "Por venir": month.is_past ? 0 : Number(month.amount),
            }))}
            dataKey="month"
            type="stacked"
            series={[
              { name: "Transcurrido", color: "gray.4" },
              { name: "Por venir", color: "obra.6" },
            ]}
            withLegend
            valueFormatter={(value) => money(value)}
            yAxisProps={{ width: 90 }}
            tickLine="y"
          />

          <Stack gap={4}>
            {projection.months.map((month) => (
              <Group key={month.month} justify="space-between" wrap="nowrap">
                <Text size="sm" c={month.is_past ? "dimmed" : undefined}>
                  {monthLabel(month.month)}
                </Text>
                <Text
                  size="sm"
                  c={month.is_past ? "dimmed" : undefined}
                  style={{ whiteSpace: "nowrap" }}
                >
                  {money(month.amount)}
                </Text>
              </Group>
            ))}
            <Divider my={4} />
            <Group justify="space-between" wrap="nowrap">
              <Text fw={600}>Total proyectado</Text>
              <Text fw={700} style={{ whiteSpace: "nowrap" }}>
                {money(projection.projected_total)}
              </Text>
            </Group>
          </Stack>

          {Number(projection.unassigned_cost) > 0 && (
            <Text size="xs" c="dimmed">
              Además hay {money(projection.unassigned_cost)} del cómputo sin
              asignar a ninguna tarea, que no entran en la proyección porque
              nadie planificó cuándo se gastan.
            </Text>
          )}
        </Stack>
      )}
    </DashboardBlock>
  );
}
