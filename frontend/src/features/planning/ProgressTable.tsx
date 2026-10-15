import { Button, Table, Text } from "@mantine/core";
import { BaselineEnd } from "./BaselineEnd";
import { formatPlanned, takesProgress } from "./progress";
import { TaskStatusBadge } from "./TaskStatusBadge";
import type { TaskOut } from "./types";

interface ProgressTableProps {
  tasks: TaskOut[];
  /** Today as "YYYY-MM-DD", which is what makes a fixed end a past one. */
  today: string;
  /** Opens the form that records a task's progress, for those who may manage
   * the planning. Omitted for everyone else, and then no actions column. */
  onRecord?: (task: TaskOut) => void;
}

/** The progress of each task against what was planned for it by today
 * (HU-16), for screens wide enough to read a table. Mobile gets ProgressCard.
 *
 * Plain numbers, like every other cell of the work's tables. The one badge
 * is "Atrasada", next to the date that makes it so, drawn like the planning's
 * "Crítica".
 *
 * A task loaded after the planning was fixed has no baseline: it says "Sin
 * fijar" where its date would be and has no planned progress. */
export function ProgressTable({ tasks, today, onRecord }: ProgressTableProps) {
  return (
    <Table.ScrollContainer minWidth={720}>
      <Table verticalSpacing="sm" highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tarea</Table.Th>
            <Table.Th>Estado</Table.Th>
            <Table.Th>Fin planificado</Table.Th>
            <Table.Th>Real</Table.Th>
            <Table.Th>Planificado</Table.Th>
            {onRecord && <Table.Th w={170} />}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {tasks.map((task) => (
            <Table.Tr key={task.id}>
              <Table.Td>
                <Text size="sm" fw={500}>
                  {task.name}
                </Text>
              </Table.Td>
              <Table.Td>
                <TaskStatusBadge status={task.status} />
              </Table.Td>
              <Table.Td>
                <BaselineEnd task={task} today={today} />
              </Table.Td>
              <Table.Td>
                <Text size="sm">{task.progress_percent}%</Text>
              </Table.Td>
              <Table.Td>
                <Text size="sm">{formatPlanned(task)}</Text>
              </Table.Td>
              {onRecord && (
                <Table.Td ta="right">
                  {takesProgress(task) && (
                    <Button
                      size="xs"
                      variant="default"
                      onClick={() => onRecord(task)}
                    >
                      Registrar avance
                    </Button>
                  )}
                </Table.Td>
              )}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
