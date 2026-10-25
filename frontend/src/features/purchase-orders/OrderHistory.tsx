import { Stack, Text, Timeline, Title } from "@mantine/core";
import { EVENT_LABELS, formatDateTime } from "./orderDisplay";
import type { OrderEvent } from "./types";

/** Who moved the order and when (HU-21), oldest first. */
export function OrderHistory({ history }: { history: OrderEvent[] }) {
  return (
    <Stack gap="sm">
      <Title order={5}>Historial</Title>
      <Timeline active={history.length - 1} bulletSize={14} lineWidth={2}>
        {history.map((event) => (
          <Timeline.Item key={event.kind} title={EVENT_LABELS[event.kind]}>
            <Text size="sm" c="dimmed">
              Por {event.by.name} el {formatDateTime(event.at)}
            </Text>
          </Timeline.Item>
        ))}
      </Timeline>
    </Stack>
  );
}
