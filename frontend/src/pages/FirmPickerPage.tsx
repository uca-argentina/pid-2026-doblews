import { Card, Stack, Text, Title, UnstyledButton } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

/** Shown when an account belongs to more than one firm. The active firm is
 * never remembered across sessions (ADR-002 section 9): picking one just
 * navigates to its URL. */
export function FirmPickerPage() {
  const { account } = useAuth();
  const navigate = useNavigate();

  return (
    <Stack maw={480} mx="auto" gap="md">
      <div>
        <Title order={3}>Elegí un estudio</Title>
        <Text c="dimmed" size="sm">
          Pertenecés a más de un estudio. Elegí con cuál querés trabajar ahora.
        </Text>
      </div>

      <Stack gap="sm">
        {account?.firms.map((firm) => (
          <UnstyledButton
            key={firm.id}
            onClick={() => navigate(`/firms/${firm.id}/projects`)}
          >
            <Card withBorder padding="md" radius="md">
              <Text fw={600}>{firm.name}</Text>
              <Text size="sm" c="dimmed">
                {firm.role.name}
              </Text>
            </Card>
          </UnstyledButton>
        ))}
      </Stack>
    </Stack>
  );
}
