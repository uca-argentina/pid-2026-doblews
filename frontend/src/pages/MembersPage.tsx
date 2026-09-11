import { Alert, Box, Center, Loader, Stack, Text, Title } from "@mantine/core";
import { useCurrentFirm } from "../features/firms/firmContext";
import { MemberCard } from "../features/members/MemberCard";
import { MembersTable } from "../features/members/MembersTable";
import { useMembers } from "../features/members/useMembers";

/** HU-2: the people of this firm, with their role and their state.
 *
 * There is no empty state: a firm always has at least its owner, and the owner
 * is the only one who gets here. */
export function MembersPage() {
  const { firm } = useCurrentFirm();
  const { data: members, isLoading, isError } = useMembers(firm.id);

  return (
    <Stack gap="md">
      <div>
        <Title order={3}>Padrón</Title>
        <Text c="dimmed" size="sm">
          Las personas de {firm.name} y su rol en el estudio.
        </Text>
      </div>

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar el padrón. Probá de nuevo en un momento.
        </Alert>
      )}

      {members && (
        <>
          {/* One list, two shapes. Both are rendered and one is hidden by CSS,
              which is how Mantine's responsive props work: no window
              measurement, and nothing to re-render on resize. */}
          <Box visibleFrom="sm">
            <MembersTable members={members} />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {members.map((member) => (
              <MemberCard key={member.account_id} member={member} />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
