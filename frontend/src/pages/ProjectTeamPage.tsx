import { useState } from "react";
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
import { useDisclosure } from "@mantine/hooks";
import { useCurrentFirm } from "../features/firms/firmContext";
import { useCurrentProject } from "../features/projects/projectContext";
import { AddTeamMemberModal } from "../features/team/AddTeamMemberModal";
import { ChangeTeamRoleModal } from "../features/team/ChangeTeamRoleModal";
import { RemoveTeamMemberModal } from "../features/team/RemoveTeamMemberModal";
import { TeamMemberCard } from "../features/team/TeamMemberCard";
import { TeamTable } from "../features/team/TeamTable";
import { useTeam } from "../features/team/useTeam";
import type { ProjectMemberOut } from "../features/team/types";

/** HU-6: who works on this work, and with which role.
 *
 * A sibling of the work's data under ProjectLayout, which has already resolved
 * the work and the caller's permissions on it: this fetches only the team.
 *
 * Split in two like the take-off screen, so the read only happens for someone
 * who may do it: the backend would answer a 403 otherwise, and asking for
 * something we already know is refused is a request for nothing. */
export function ProjectTeamPage() {
  const { firm } = useCurrentFirm();
  const { project, can } = useCurrentProject();

  if (!can("project.member.view")) {
    // The tab is already hidden; this answers someone who typed the URL.
    return (
      <Alert color="red" variant="light" title="No tenés permiso">
        Tu rol en esta obra no incluye ver su equipo.
      </Alert>
    );
  }

  return (
    <TeamView
      firmId={firm.id}
      projectId={project.id}
      canManage={can("project.member.manage")}
    />
  );
}

/** There is no empty state. A work always has a lead — create_project assigns
 * its creator in the same transaction — and the lead cannot be taken off, so
 * the list is never empty. */
function TeamView({
  firmId,
  projectId,
  canManage,
}: {
  firmId: number;
  projectId: number;
  canManage: boolean;
}) {
  const { data: team, isLoading, isError } = useTeam(firmId, projectId);
  const [addOpened, addModal] = useDisclosure(false);
  // Which member a modal is about, and null when it is closed. Kept here and
  // not inside each row so there is one modal of each kind on the screen
  // rather than one per person.
  const [roleTarget, setRoleTarget] = useState<ProjectMemberOut | null>(null);
  const [removeTarget, setRemoveTarget] = useState<ProjectMemberOut | null>(
    null,
  );

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <div>
          <Title order={4}>Equipo</Title>
          <Text c="dimmed" size="sm">
            Quiénes participan de esta obra y qué puede hacer cada uno.
          </Text>
        </div>
        {canManage && (
          <Button onClick={addModal.open}>Agregar al equipo</Button>
        )}
      </Group>

      {/* Outside the loading branches on purpose, as in the take-off: a modal
          rendered inside one would be torn down mid-close when the list
          refreshes behind it. Only for those who may manage the team: a button
          that fails is worse than none. */}
      {canManage && (
        <>
          <AddTeamMemberModal opened={addOpened} onClose={addModal.close} />
          <ChangeTeamRoleModal
            member={roleTarget}
            onClose={() => setRoleTarget(null)}
          />
          <RemoveTeamMemberModal
            member={removeTarget}
            onClose={() => setRemoveTarget(null)}
          />
        </>
      )}

      {isLoading && (
        <Center>
          <Loader />
        </Center>
      )}

      {isError && (
        <Alert color="red" variant="light">
          No pudimos cargar el equipo. Probá de nuevo en un momento.
        </Alert>
      )}

      {team && (
        <>
          {/* One list, two shapes. Both are rendered and one is hidden by CSS,
              which is how Mantine's responsive props work: no window
              measurement, and nothing to re-render on resize. */}
          <Box visibleFrom="sm">
            <TeamTable
              members={team}
              onChangeRole={setRoleTarget}
              onRemove={setRemoveTarget}
            />
          </Box>
          <Stack gap="sm" hiddenFrom="sm">
            {team.map((member) => (
              <TeamMemberCard
                key={member.account_id}
                member={member}
                onChangeRole={setRoleTarget}
                onRemove={setRemoveTarget}
              />
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
