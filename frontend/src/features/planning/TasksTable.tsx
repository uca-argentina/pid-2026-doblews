import type { ReactNode } from "react";
import { Table, Text, UnstyledButton } from "@mantine/core";
import { formatMoney } from "../../lib/format";
import { EMPTY } from "../projects/projectFields";
import { SlackBadge } from "./SlackBadge";
import { formatDuration, taskEnd, taskStart } from "./taskFields";
import { TaskDateText } from "./TaskDateText";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface TasksTableProps {
  tasks: TaskOut[];
  currency: string;
  /** Whether the response carries costs at all. Decided once by the page from
   * total_cost, so the column is there for every row or for none. */
  showsCost: boolean;
  /** Opens the task's detail, from its name. */
  onOpen: (task: TaskOut) => void;
  /** The status as a control that changes it, for those who may manage the
   * planning. Omitted for everyone else, who get the plain badge. */
  renderStatus?: (task: TaskOut) => ReactNode;
  /** What each task offers to do, for those who may manage the planning.
   * Omitted for everyone else, and then no actions column. */
  renderActions?: (task: TaskOut) => ReactNode;
}

/** The planning as a table, for screens wide enough to read one. Mobile gets
 * TaskCard instead (frontend/CLAUDE.md: cards, never a horizontal table).
 *
 * The order is the backend's: by planned start, so the list reads in time
 * (HU-14), and in the order they were loaded where that ties.
 *
 * "Inicio" and "Fin" are one column each and not two: the planned date is
 * the actual one once it happened, so showing both would repeat it. The text
 * says which one it is — plain when actual, dimmed when planned. */
export function TasksTable({
  tasks,
  currency,
  showsCost,
  onOpen,
  renderStatus,
  renderActions,
}: TasksTableProps) {
  return (
    <Table.ScrollContainer minWidth={860}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tarea</Table.Th>
            <Table.Th>Responsable</Table.Th>
            <Table.Th>Duración</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th>Inicio</Table.Th>
            <Table.Th>Fin</Table.Th>
            <Table.Th>Holgura</Table.Th>
            {showsCost && <Table.Th ta="right">Costo</Table.Th>}
            {/* No heading, like the team's actions column: the menu's own
                label says what it does. */}
            {renderActions && <Table.Th w={60} />}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {tasks.map((task) => (
            <Table.Tr key={task.id}>
              <Table.Td>
                <UnstyledButton
                  onClick={() => onOpen(task)}
                  aria-label={`Ver el detalle de ${task.name}`}
                >
                  <Text size="sm" fw={500} td="underline">
                    {task.name}
                  </Text>
                </UnstyledButton>
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
                {renderStatus?.(task) ?? (
                  <TaskStatusBadge status={task.status} />
                )}
              </Table.Td>
              <Table.Td>
                <TaskDateText date={taskStart(task)} />
              </Table.Td>
              <Table.Td>
                <TaskDateText date={taskEnd(task)} />
              </Table.Td>
              <Table.Td>
                <SlackBadge task={task} />
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
