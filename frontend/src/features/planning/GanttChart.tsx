import { useEffect, useRef, useState } from "react";
import { Box, Stack, Text, Tooltip, UnstyledButton } from "@mantine/core";
import { useElementSize, useMergedRef } from "@mantine/hooks";
import { formatDate } from "../projects/projectFields";
import {
  atLeast,
  DAY_WIDTH,
  elapsedDays,
  ganttBar,
  ganttHeader,
  ganttRange,
  isWeekend,
  toDay,
  todayDay,
  type GanttCell,
  type GanttRange,
  type GanttScale,
} from "./ganttScale";
import { GanttToolbar } from "./GanttToolbar";
import { STATUS_COLORS, STATUS_LABELS } from "./taskStatus";
import type { TaskOut } from "./types";

interface GanttChartProps {
  /** In the planning's own order: by planned start, so the bars step down
   * and to the right. */
  tasks: TaskOut[];
  projectStartDate: string | null;
  /** When the work is planned to end. */
  plannedEndDate: string | null;
  /** Opens the task's detail, from its name or from its bar. */
  onOpen: (task: TaskOut) => void;
}

const NAMES_WIDTH = 220;
const HEADER_ROW_HEIGHT = 28;
/** The strip under the header that names the two marked days. */
const MARKS_ROW_HEIGHT = 22;
const ROW_HEIGHT = 40;
const BAR_HEIGHT = 20;
const LINE = "1px solid var(--mantine-color-gray-3)";
const MARK_COLOR = "var(--mantine-color-text)";

/** The planning in time (HU-15): one row per task, its bar running from its
 * start to its end over an axis of days.
 *
 * Read only, and it draws no dependencies: those are read in each task's
 * detail, which a name or a bar opens, and which is also where a task is
 * edited from (ADR-009 section 12).
 *
 * Two columns side by side and not one wide table: the names stay put and
 * only the axis scrolls sideways. Both stack rows of the same height, which
 * is what keeps a name level with its bar.
 *
 * The whole work is drawn, not a window of it: moving back and forward is
 * scrolling the axis, so there is no "visible range" to keep in state. */
export function GanttChart({
  tasks,
  projectStartDate,
  plannedEndDate,
  onOpen,
}: GanttChartProps) {
  const [scale, setScale] = useState<GanttScale>("week");
  const dayWidth = DAY_WIDTH[scale];
  const today = todayDay();

  // The axis covers the work, and at least the width there is to draw on: it
  // is measured, because how many weeks fit depends on the window.
  const { ref: sizeRef, width: axisWidth } = useElementSize();
  const axis = useRef<HTMLDivElement>(null);
  const axisRef = useMergedRef(sizeRef, axis);
  const range = atLeast(
    ganttRange(tasks, projectStartDate, plannedEndDate, today),
    Math.ceil(axisWidth / dayWidth),
  );
  const header = ganttHeader(range, scale);

  // Today is marked at noon, the middle of its day, and the end of the work
  // at the close of its last day: the right edge of the last bar.
  const todayLeft = (today - range.start + 0.5) * dayWidth;
  const endLeft =
    plannedEndDate === null
      ? null
      : (toDay(plannedEndDate) - range.start + 1) * dayWidth;

  const scrollToToday = (behavior: ScrollBehavior) => {
    const element = axis.current;
    if (!element) return;
    element.scrollTo({
      left: todayLeft - element.clientWidth / 2,
      behavior,
    });
  };
  const scrollByScreens = (screens: number) => {
    const element = axis.current;
    // Not a whole screen: what was at one edge stays in sight at the other.
    element?.scrollBy({
      left: screens * element.clientWidth * 0.8,
      behavior: "smooth",
    });
  };

  // Opens on today, and comes back to it when the scale changes: zooming
  // would otherwise leave the view wherever the same scroll offset lands.
  // Waits for the first measurement, before which there is no width to
  // centre in; a resize after that moves nothing.
  const measured = axisWidth > 0;
  useEffect(() => {
    const element = axis.current;
    if (measured && element) {
      element.scrollLeft = todayLeft - element.clientWidth / 2;
    }
  }, [measured, todayLeft]);

  return (
    <Stack gap="sm">
      <GanttToolbar
        scale={scale}
        onScaleChange={setScale}
        onPrevious={() => scrollByScreens(-1)}
        onToday={() => scrollToToday("smooth")}
        onNext={() => scrollByScreens(1)}
      />

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
          <Box
            h={HEADER_ROW_HEIGHT * 2 + MARKS_ROW_HEIGHT}
            style={{ borderBottom: LINE }}
          />
          {tasks.map((task) => (
            <Box
              key={task.id}
              h={ROW_HEIGHT}
              px="sm"
              style={{ display: "flex", alignItems: "center" }}
            >
              <UnstyledButton
                className="name-link"
                onClick={() => onOpen(task)}
                aria-label={`Ver el detalle de ${task.name}`}
                title={task.name}
                maw="100%"
              >
                <Text size="sm" fw={500} c="inherit" truncate>
                  {task.name}
                </Text>
              </UnstyledButton>
            </Box>
          ))}
        </Box>

        <Box ref={axisRef} style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
          <Box w={range.days * dayWidth} pos="relative">
            <HeaderRow cells={header.top} dayWidth={dayWidth} strong />
            <HeaderRow cells={header.bottom} dayWidth={dayWidth} />

            <Box
              h={MARKS_ROW_HEIGHT}
              pos="relative"
              style={{ borderBottom: LINE }}
            >
              <MarkLabel left={todayLeft} align="center">
                Hoy
              </MarkLabel>
              {endLeft !== null && (
                <MarkLabel left={endLeft} align="left">
                  Fin previsto
                </MarkLabel>
              )}
            </Box>

            <Box pos="relative">
              {/* The grid: one line per cell of the scale, behind every row.
                  Day by day, the weekends are shaded: nothing is planned on
                  them, and a bar crossing one is not working those days. */}
              {header.bottom.map((cell) => (
                <Box
                  key={cell.offset}
                  pos="absolute"
                  top={0}
                  bottom={0}
                  left={cell.offset * dayWidth}
                  w={cell.days * dayWidth}
                  bg={
                    scale === "day" && isWeekend(range.start + cell.offset)
                      ? "var(--mantine-color-gray-0)"
                      : undefined
                  }
                  style={{
                    borderLeft: "1px solid var(--mantine-color-gray-1)",
                  }}
                />
              ))}

              {tasks.map((task) => (
                <Box key={task.id} h={ROW_HEIGHT} pos="relative">
                  <Bar
                    task={task}
                    range={range}
                    dayWidth={dayWidth}
                    today={today}
                    onOpen={onOpen}
                  />
                </Box>
              ))}

              <MarkLine left={todayLeft} />
              {endLeft !== null && <MarkLine left={endLeft} dashed />}
            </Box>
          </Box>
        </Box>
      </Box>
    </Stack>
  );
}

/** One task on the axis.
 *
 * The colour is its status, the same as its badge in the list. What is
 * already behind it is solid and what is still expected is pale: the same
 * difference the list makes between a date in black and one in grey. A
 * critical task swaps its border for a red one, as its card does on a phone.
 *
 * It is a button: pressing it opens the task's detail. Hovering says what
 * the bar alone cannot — the exact dates, which the axis only approximates
 * at the wider scales. */
function Bar({
  task,
  range,
  dayWidth,
  today,
  onOpen,
}: {
  task: TaskOut;
  range: GanttRange;
  dayWidth: number;
  today: number;
  onOpen: (task: TaskOut) => void;
}) {
  const bar = ganttBar(task, range);
  // No start date on the work: the row stays, with nothing to draw in it.
  if (!bar) return null;

  const color = STATUS_COLORS[task.status];
  return (
    <Tooltip
      withArrow
      label={
        <>
          <Text size="xs" fw={600}>
            {task.name}
          </Text>
          <Text size="xs">
            {formatDate(task.planned_start_date)} →{" "}
            {formatDate(task.planned_end_date)}
          </Text>
          <Text size="xs">
            {STATUS_LABELS[task.status]}
            {task.is_critical && " · Crítica"}
          </Text>
        </>
      }
    >
      <UnstyledButton
        onClick={() => onOpen(task)}
        aria-label={`Ver el detalle de ${task.name}`}
        pos="absolute"
        top={(ROW_HEIGHT - BAR_HEIGHT) / 2}
        h={BAR_HEIGHT}
        left={bar.offset * dayWidth}
        w={bar.days * dayWidth}
        bg={`var(--mantine-color-${color}-light)`}
        style={{
          border: task.is_critical
            ? "2px solid var(--mantine-color-red-filled)"
            : `1px solid var(--mantine-color-${color}-filled)`,
          borderRadius: "var(--mantine-radius-default)",
          overflow: "hidden",
        }}
      >
        <Box
          h="100%"
          w={elapsedDays(task, bar, range, today) * dayWidth}
          bg={`var(--mantine-color-${color}-filled)`}
        />
      </UnstyledButton>
    </Tooltip>
  );
}

/** A day marked across every row: today, solid, or the planned end of the
 * work, dashed. */
function MarkLine({
  left,
  dashed = false,
}: {
  left: number;
  dashed?: boolean;
}) {
  return (
    <Box
      pos="absolute"
      top={0}
      bottom={0}
      left={left}
      style={{
        borderLeft: `2px ${dashed ? "dashed" : "solid"} ${MARK_COLOR}`,
        pointerEvents: "none",
      }}
    />
  );
}

/** What a marked day is, in the strip above the rows: centred on its line, or
 * starting at it. */
function MarkLabel({
  left,
  align,
  children,
}: {
  left: number;
  align: "center" | "left";
  children: string;
}) {
  return (
    <Text
      size="xs"
      fw={600}
      pos="absolute"
      top={2}
      left={left}
      px={4}
      style={{
        whiteSpace: "nowrap",
        transform: align === "center" ? "translateX(-50%)" : undefined,
      }}
    >
      {children}
    </Text>
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
