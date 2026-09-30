import type { ReactNode } from "react";
import { Group, Text, Title, type TitleOrder } from "@mantine/core";

interface PageHeaderProps {
  title: string;
  description?: string;
  /** The primary action, at the right of the title on a wide screen and
   * wrapping onto its own line below the title on a narrow one. Optional:
   * some headers have no action, or gate it behind a permission. */
  action?: ReactNode;
  /** Title level, 3 by default. A header nested in a section (ProjectTeamPage's
   * "Equipo") passes 4. */
  order?: TitleOrder;
}

/** The title/description/action row every list screen opens with.
 *
 * wrap="wrap" is what makes it responsive: the text block grows to push the
 * action to the right on a wide screen, and once there is no room for both the
 * text's minWidth and the action, the action wraps below, left-aligned. */
export function PageHeader({
  title,
  description,
  action,
  order = 3,
}: PageHeaderProps) {
  return (
    <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
      <div style={{ flex: 1, minWidth: 220 }}>
        <Title order={order}>{title}</Title>
        {description && (
          <Text c="dimmed" size="sm">
            {description}
          </Text>
        )}
      </div>
      {action}
    </Group>
  );
}
