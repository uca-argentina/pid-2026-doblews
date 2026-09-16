import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { projectKeys } from "../projects/useProjects";
import {
  addTeamMember,
  changeTeamRole,
  fetchTeam,
  fetchTeamRoles,
  removeTeamMember,
} from "./teamService";
import type { AssignableProjectRole, ProjectMemberAdd } from "./types";

/** The team hangs below its work's key, like the take-off, so editing the work
 * refreshes it too and nothing about another work or firm is touched here. */
export const teamKeys = {
  one: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "team"] as const,
  roles: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "team-roles"] as const,
};

/** The team of one work, the people who left the firm included. */
export function useTeam(firmId: number, projectId: number) {
  return useQuery({
    queryKey: teamKeys.one(firmId, projectId),
    queryFn: () => fetchTeam(firmId, projectId),
  });
}

/** The options of every "rol" <Select> in this section.
 *
 * staleTime: Infinity because the role catalogue is seeded by migration and
 * cannot change during a session — the same reasoning as useMemberRoles.
 * Shared through the query cache, so the add and the edit forms fetch it once
 * between them. */
export function useTeamRoles(firmId: number, projectId: number) {
  return useQuery({
    queryKey: teamKeys.roles(firmId, projectId),
    queryFn: () => fetchTeamRoles(firmId, projectId),
    staleTime: Infinity,
  });
}

/** Every write below invalidates the whole projects subtree of this firm, and
 * not just the team.
 *
 * That looks wider than it needs to be and is not. HU-6 asks that the client
 * assigned here be "el mismo que muestra el listado de obras de HU-3: una sola
 * fuente, no dos lugares donde cargar lo mismo" — and it is one
 * project_member row, so a team write can change what the work's own header
 * ("Cliente: …") and the listing print. Refreshing only the team would leave
 * both showing a client that is no longer there, which reads as the data being
 * wrong rather than as a stale cache.
 *
 * The team's key hangs below the work's, so this one invalidation covers it
 * too. It is the same call useUpdateProject makes, for the same reason.
 *
 * Returning it from onSuccess keeps the mutation pending until the refetch
 * lands, so a modal closes onto a list that already shows the change.
 *
 * Errors are not handled here: the modals render them next to the form, where
 * a 409 about a transfer or a second client can be acted on. */
function useTeamWrite<Variables, Result>(
  firmId: number,
  write: (variables: Variables) => Promise<Result>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: write,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: projectKeys.all(firmId) }),
  });
}

/** Puts someone from the roster on the work. */
export function useAddTeamMember(firmId: number, projectId: number) {
  return useTeamWrite(firmId, (payload: ProjectMemberAdd) =>
    addTeamMember(firmId, projectId, payload),
  );
}

/** Gives someone already on the work another role on it. */
export function useChangeTeamRole(firmId: number, projectId: number) {
  return useTeamWrite(
    firmId,
    (variables: { accountId: number; roleCode: AssignableProjectRole }) =>
      changeTeamRole(firmId, projectId, variables.accountId, {
        role_code: variables.roleCode,
      }),
  );
}

/** Takes someone off the work. They stop seeing it on their next request. */
export function useRemoveTeamMember(firmId: number, projectId: number) {
  return useTeamWrite(firmId, (accountId: number) =>
    removeTeamMember(firmId, projectId, accountId),
  );
}
