import type { ReactNode } from "react";
import { Table, Text } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { EMPTY, formatDate } from "../projects/projectFields";
import { formatDuration } from "./taskFields";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface TasksTableProps {
  tasks: TaskOut[];
  currency: string;
  /** Whether the response carries costs at all. Decided once by the page from
   * total_cost, so the column is there for every row or for none. */
  showsCost: boolean;
  /** What each task offers to do, for those who may manage the planning.
   * Omitted for everyone else, and then no actions column. */
  renderActions?: (task: TaskOut) => ReactNode;
}

/** The planning as a table, for screens wide enough to read one. Mobile gets
 * TaskCard instead (frontend/CLAUDE.md: cards, never a horizontal table).
 *
 * The order is the backend's — the order the tasks were loaded in — so
 * nothing reshuffles between reloads or when one is renamed. HU-14 is what
 * will order them in time. */
export function TasksTable({
  tasks,
  currency,
  showsCost,
  renderActions,
}: TasksTableProps) {
  return (
    <Table.ScrollContainer minWidth={760}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tarea</Table.Th>
            <Table.Th>Responsable</Table.Th>
            <Table.Th>Duración</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th>Inicio real</Table.Th>
            <Table.Th>Fin real</Table.Th>
            {showsCost && <Table.Th ta="right">Costo</Table.Th>}
            {/* No heading, like the team's actions column: the buttons say
                what they do. */}
            {renderActions && <Table.Th />}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {tasks.map((task) => (
            <Table.Tr key={task.id}>
              <Table.Td>
                <Text size="sm" fw={500}>
                  {task.name}
                </Text>
                {task.description && (
                  <Text size="xs" c="dimmed" lineClamp={2}>
                    {task.description}
                  </Text>
                )}
              </Table.Td>
              <Table.Td>
                <Text size="sm" c={task.assignee ? undefined : "dimmed"}>
                  {task.assignee?.name ?? "Sin responsable"}
                </Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm" style={{ whiteSpace: "nowrap" }}>
                  {formatDuration(task.estimated_duration_days)}
                </Text>
              </Table.Td>
              <Table.Td>
                <TaskStatusBadge status={task.status} />
              </Table.Td>
              <Table.Td>
                <Text size="sm">{formatDate(task.actual_start_date)}</Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{formatDate(task.actual_end_date)}</Text>
              </Table.Td>
              {showsCost && (
                <Table.Td ta="right">
                  <Text size="sm" style={{ whiteSpace: "nowrap" }}>
                    {task.cost !== null
                      ? formatMoney(task.cost, currency)
                      : EMPTY}
                  </Text>
                </Table.Td>
              )}
              {renderActions && <Table.Td>{renderActions(task)}</Table.Td>}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
