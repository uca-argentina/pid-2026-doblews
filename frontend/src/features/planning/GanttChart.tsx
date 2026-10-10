import { Box, Text } from "@mantine/core";
import { useElementSize } from "@mantine/hooks";
import {
  atLeast,
  DAY_WIDTH,
  ganttBar,
  ganttHeader,
  ganttRange,
  todayDay,
  type GanttCell,
  type GanttScale,
} from "./ganttScale";
import { STATUS_COLORS } from "./taskStatus";
import type { TaskOut } from "./types";

interface GanttChartProps {
  /** In the planning's own order: by planned start, so the bars step down
   * and to the right. */
  tasks: TaskOut[];
  projectStartDate: string | null;
  /** When the work is planned to end. */
  plannedEndDate: string | null;
  scale?: GanttScale;
}

const NAMES_WIDTH = 220;
const HEADER_ROW_HEIGHT = 28;
const ROW_HEIGHT = 40;
const BAR_HEIGHT = 20;
const LINE = "1px solid var(--mantine-color-gray-3)";

/** The planning in time (HU-15): one row per task, its bar running from its
 * start to its end over an axis of days.
 *
 * Read only, and it draws no dependencies: those are read in each task's
 * detail (ADR-009 section 12).
 *
 * Two columns side by side and not one wide table: the names stay put and
 * only the axis scrolls sideways. Both stack rows of the same height, which
 * is what keeps a name level with its bar. */
export function GanttChart({
  tasks,
  projectStartDate,
  plannedEndDate,
  scale = "week",
}: GanttChartProps) {
  const dayWidth = DAY_WIDTH[scale];
  // The axis covers the work, and at least the width there is to draw on: it
  // is measured, because how many weeks fit depends on the window.
  const { ref: axisRef, width: axisWidth } = useElementSize();
  const range = atLeast(
    ganttRange(tasks, projectStartDate, plannedEndDate, todayDay()),
    Math.ceil(axisWidth / dayWidth),
  );
  const header = ganttHeader(range, scale);

  return (
    <Box
      bg="var(--mantine-color-body)"
      style={{
        display: "flex",
        border: LINE,
        borderRadius: "var(--mantine-radius-default)",
        overflow: "hidden",
      }}
    >
      <Box w={NAMES_WIDTH} style={{ flexShrink: 0, borderRight: LINE }}>
        <Box h={HEADER_ROW_HEIGHT * 2} style={{ borderBottom: LINE }} />
        {tasks.map((task) => (
          <Box
            key={task.id}
            h={ROW_HEIGHT}
            px="sm"
            style={{ display: "flex", alignItems: "center" }}
          >
            <Text size="sm" fw={500} truncate title={task.name}>
              {task.name}
            </Text>
          </Box>
        ))}
      </Box>

      <Box ref={axisRef} style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
        <Box w={range.days * dayWidth} pos="relative">
          <HeaderRow cells={header.top} dayWidth={dayWidth} strong />
          <HeaderRow cells={header.bottom} dayWidth={dayWidth} />

          <Box pos="relative">
            {/* The grid: one line per cell of the scale, behind every row. */}
            {header.bottom.map((cell) => (
              <Box
                key={cell.offset}
                pos="absolute"
                top={0}
                bottom={0}
                left={cell.offset * dayWidth}
                style={{ borderLeft: "1px solid var(--mantine-color-gray-1)" }}
              />
            ))}

            {tasks.map((task) => {
              const bar = ganttBar(task, range);
              return (
                <Box key={task.id} h={ROW_HEIGHT} pos="relative">
                  {bar && (
                    <Box
                      pos="absolute"
                      top={(ROW_HEIGHT - BAR_HEIGHT) / 2}
                      h={BAR_HEIGHT}
                      left={bar.offset * dayWidth}
                      w={bar.days * dayWidth}
                      bg={`var(--mantine-color-${STATUS_COLORS[task.status]}-filled)`}
                      style={{ borderRadius: "var(--mantine-radius-default)" }}
                    />
                  )}
                </Box>
              );
            })}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

/** One row of the header: its cells side by side, each as wide as the days it
 * covers. A label that does not fit its cell is cut, not wrapped — the first
 * month of the axis is often only a few days of it. */
function HeaderRow({
  cells,
  dayWidth,
  strong = false,
}: {
  cells: GanttCell[];
  dayWidth: number;
  strong?: boolean;
}) {
  return (
    <Box h={HEADER_ROW_HEIGHT} pos="relative" style={{ borderBottom: LINE }}>
      {cells.map((cell) => (
        <Box
          key={cell.offset}
          pos="absolute"
          top={0}
          bottom={0}
          left={cell.offset * dayWidth}
          w={cell.days * dayWidth}
          px={6}
          style={{
            display: "flex",
            alignItems: "center",
            overflow: "hidden",
            borderLeft: cell.offset === 0 ? undefined : LINE,
          }}
        >
          <Text
            size="xs"
            fw={strong ? 600 : undefined}
            c={strong ? undefined : "dimmed"}
            style={{ whiteSpace: "nowrap" }}
          >
            {cell.label}
          </Text>
        </Box>
      ))}
    </Box>
  );
}
