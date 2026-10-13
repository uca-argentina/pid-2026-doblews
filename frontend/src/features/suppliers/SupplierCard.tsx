import { Card, Group, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { SupplierActionsMenu } from "./SupplierActionsMenu";
import type { SupplierOut } from "./types";

interface SupplierCardProps {
  firmId: number;
  supplier: SupplierOut;
  onEdit: (supplier: SupplierOut) => void;
  onDeactivate: (supplier: SupplierOut) => void;
}

/** One supplier on a phone. Same data as a table row, stacked instead of side
 * by side, so 375px needs no horizontal scrolling. The email is truncated
 * rather than wrapped: it is the longest field by far. */
export function SupplierCard({
  firmId,
  supplier,
  onEdit,
  onDeactivate,
}: SupplierCardProps) {
  const contact = [supplier.contact_name, supplier.phone]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card withBorder padding="md" radius="md">
      <Stack gap={4}>
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text
            component={Link}
            to={`/firms/${firmId}/suppliers/${supplier.id}`}
            fw={600}
            c="inherit"
            truncate
          >
            {supplier.name}
          </Text>
          <SupplierActionsMenu
            supplier={supplier}
            onEdit={onEdit}
            onDeactivate={onDeactivate}
          />
        </Group>
        {contact && <Text size="sm">{contact}</Text>}
        {supplier.contact_email && (
          <Text size="sm" c="dimmed" truncate>
            {supplier.contact_email}
          </Text>
        )}
        <Text size="sm" c="dimmed">
          {supplier.price_count === 1
            ? "1 material en su lista"
            : `${supplier.price_count} materiales en su lista`}
        </Text>
      </Stack>
    </Card>
  );
}
