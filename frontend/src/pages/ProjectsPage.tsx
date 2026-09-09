import { useQuery } from "@tanstack/react-query";
import { Alert, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { FirmSummary } from "../features/auth/types";

/** Placeholder landing screen for HU-1: it exists so there is somewhere real
 * to redirect to and to prove the firm-scoped route works end to end. The
 * actual listing is HU-3.
 *
 * Fetching GET /firms/{firmId} here — instead of trusting the firm list
 * already in the account from /auth/me — is what turns a stale or foreign
 * firm id typed into the URL into the backend's 404, rather than rendering
 * with no data. */
export function ProjectsPage() {
  const { firmId } = useParams<{ firmId: string }>();

  const {
    data: firm,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["firm", firmId],
    queryFn: async () => {
      const { data } = await api.get<FirmSummary>(`/firms/${firmId}`);
      return data;
    },
    enabled: Boolean(firmId),
    retry: false,
  });

  if (isLoading) {
    return (
      <Center>
        <Loader />
      </Center>
    );
  }

  if (isError || !firm) {
    return (
      <Alert color="red" variant="light">
        No encontramos ese estudio, o no formás parte de él.
      </Alert>
    );
  }

  return (
    <Stack gap="xs">
      <Title order={3}>{firm.name}</Title>
      <Text c="dimmed" size="sm">
        Rol: {firm.role.name}
      </Text>
      <Text mt="lg">Listado de obras — próximamente.</Text>
    </Stack>
  );
}
