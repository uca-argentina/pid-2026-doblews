import type { ReactNode } from "react";
import { Anchor, Card, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

/** One block of the dashboard: a card with its title, and either its content
 * or what is missing for it to have any (HU-19: "cada bloque tiene su estado
 * vacío y dice qué falta cargar"). */
export function DashboardBlock({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <Card withBorder padding="lg" radius="md" h="100%">
      <Stack gap="md">
        <Title order={5}>{title}</Title>
        {children}
      </Stack>
    </Card>
  );
}

/** What a block shows with no data: what is missing, and where to load it. */
export function MissingData({
  children,
  to,
  linkLabel,
}: {
  children: ReactNode;
  /** The section that loads what is missing, when the caller may go there. */
  to?: string;
  linkLabel?: string;
}) {
  return (
    <Stack gap={4}>
      <Text size="sm" c="dimmed">
        {children}
      </Text>
      {to && linkLabel && (
        <Anchor component={Link} to={to} size="sm">
          {linkLabel} →
        </Anchor>
      )}
    </Stack>
  );
}

/** A label over a value, as every block lays out its numbers. */
export function Figure({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: ReactNode;
}) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={600} size="lg">
        {children}
      </Text>
      {hint && (
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      )}
    </div>
  );
}
