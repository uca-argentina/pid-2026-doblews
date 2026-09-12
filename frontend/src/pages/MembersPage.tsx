import {
  Alert,
  Box,
  Button,
  Center,
  Group,
  Loader,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useState } from "react";
import { useDisclosure } from "@mantine/hooks";
import { useCurrentFirm } from "../features/firms/firmContext";
import { AddMemberModal } from "../features/members/AddMemberModal";
import { ChangeRoleModal } from "../features/members/ChangeRoleModal";
import { MemberCard } from "../features/members/MemberCard";
import { MembersTable } from "../features/members/MembersTable";
import { ReinstateMemberModal } from "../features/members/ReinstateMemberModal";
import { RemoveMemberModal } from "../features/members/RemoveMemberModal";
import { useMembers } from "../features/members/useMembers";
import type { MemberOut } from "../features/members/types";

/** HU-2: the people of this firm, with their role and their state.
 *
 * There is no empty state: a firm always has at least its owner, and the owner
 * is the only one who gets here. */
export function MembersPage() {
  const { firm } = useCurrentFirm();
  const { data: members, isLoading, isError } = useMembers(firm.id);
  const [addOpened, addModal] = useDisclosure(false);
  // Which member a modal is about, and null when it is closed. Kept here and
  // not inside each row so there is one modal of each kind on the screen
  // rather than one per person.
  const [roleTarget, setRoleTarget] = useState<MemberOut | null>(null);
  const [removeTarget, setRemoveTarget] = useState<MemberOut | null>(null);
  const [reinstateTarget, setReinstateTarget] = useState<MemberOut | null>(
    null,
  );

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <div>
          <Title order={3}>Padrón</Title>
          <Text c="dimmed" size="sm">
            Las personas de {firm.name} y su rol en el estudio.
          </Text>
        </div>
        {/* No permission check: this whole screen already sits behind
            member.add, the permission the add itself demands. */}
        <Button onClick={addModal.open}>Agregar miembro</Button>
      </Group>

      <AddMemberModal opened={addOpened} onClose={addModal.close} />
      <ChangeRoleModal
        member={roleTarget}
        onClose={() => setRoleTarget(null)}
      />
      <RemoveMemberModal
        member={removeTarget}
        onClose={() => setRemoveTarget(null)}
      />
      <ReinstateMemberModal
        member={reinstateTarget}
        onClose={() => setReinstateTarget(null)}
      />

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
            <MembersTable
              members={members}
              onChangeRole={setRoleTarget}
              onRemove={setRemoveTarget}
              onReinstate={setReinstateTarget}
            />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {members.map((member) => (
              <MemberCard
                key={member.account_id}
                member={member}
                onChangeRole={setRoleTarget}
                onRemove={setRemoveTarget}
                onReinstate={setReinstateTarget}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
