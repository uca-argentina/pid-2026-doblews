import { Group, SimpleGrid, Text } from "@mantine/core";
import dayjs from "dayjs";
import { formatMoney } from "../../lib/format";
import { DashboardBlock, Figure, MissingData } from "./DashboardBlock";
import type { BudgetComparisonOut } from "./types";

/** Over budget is red and under is green: what the architect looks for is
 * the money going up. */
const DIRECTION = {
  above: { color: "red", arrow: "▲", label: "por encima del original" },
  below: { color: "obra", arrow: "▼", label: "por debajo del original" },
  equal: { color: "dimmed", arrow: "=", label: "igual al original" },
} as const;

/** Presupuesto original vs. actualizado (HU-19, D-17).
 *
 * The original is the work's v1, the first budget saved; the updated one is
 * the live budget, the same total the take-off shows today. Both say which
 * prices they are at, since that is most of why they differ. */
export function BudgetBlock({
  budget,
  currency,
  versionsPath,
}: {
  budget: BudgetComparisonOut;
  currency: string;
  /** The saved budgets tab, where the original is saved. */
  versionsPath: string;
}) {
  const { original } = budget;

  return (
    <DashboardBlock title="Presupuesto original vs. actualizado">
      {original === null || budget.direction === null ? (
        <MissingData to={versionsPath} linkLabel="Ir a Presupuestos">
          Todavía no hay un presupuesto original. Guardá una versión del
          presupuesto: la primera que se guarda es la original.
        </MissingData>
      ) : (
        <>
          <SimpleGrid cols={{ base: 1, xs: 2 }} spacing="md">
            <Figure
              label={`Original (v${original.version_number})`}
              hint={`${original.note ? `${original.note} · ` : ""}guardado el ${dayjs(original.created_at).format("DD/MM/YYYY")}`}
            >
              {formatMoney(original.total, currency)}
            </Figure>
            <Figure
              label="Actualizado"
              hint={
                budget.prices_as_of
                  ? `Cómputo de hoy, precios de referencia al ${dayjs(budget.prices_as_of).format("DD/MM/YYYY")}`
                  : "Cómputo de hoy"
              }
            >
              {formatMoney(budget.updated_total, currency)}
            </Figure>
          </SimpleGrid>

          <Group gap="xs" align="baseline" wrap="wrap">
            <Text fw={700} c={DIRECTION[budget.direction].color}>
              {DIRECTION[budget.direction].arrow}{" "}
              {formatMoney(budget.difference ?? "0", currency)}
              {budget.difference_percent !== null &&
                ` (${formatPercent(budget.difference_percent)})`}
            </Text>
            <Text size="sm" c="dimmed">
              {DIRECTION[budget.direction].label}
            </Text>
          </Group>
        </>
      )}
    </DashboardBlock>
  );
}

/** "12.5" → "+12,5 %": signed, with the decimal comma. */
function formatPercent(value: string): string {
  const number = Number(value);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toLocaleString("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %`;
}
