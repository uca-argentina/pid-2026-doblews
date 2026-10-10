import { api } from "../../lib/api";
import type { RoleOut } from "../auth/types";
import type {
  ProjectMemberAdd,
  ProjectMemberOut,
  ProjectMemberRoleUpdate,
} from "./types";

/** Every call the team section makes. One module so the URLs live in one
 * place, and the hooks in useTeam.ts stay about caching. */

function teamUrl(firmId: number, projectId: number): string {
  return `/firms/${firmId}/projects/${projectId}/members`;
}

/** The whole team, including whoever left the firm: their seat is still theirs
 * and the section says so rather than hiding it. */
export async function fetchTeam(
  firmId: number,
  projectId: number,
): Promise<ProjectMemberOut[]> {
  const { data } = await api.get<ProjectMemberOut[]>(
    teamUrl(firmId, projectId),
  );
  return data;
}

/** The three project roles, read from the API so the labels are the seeded
 * ones ("Responsable", "Colaborador", "Cliente") and this app keeps no
 * dictionary of its own. */
export async function fetchTeamRoles(
  firmId: number,
  projectId: number,
): Promise<RoleOut[]> {
  const { data } = await api.get<RoleOut[]>(
    `${teamUrl(firmId, projectId)}/roles`,
  );
  return data;
}

/** Puts someone from the firm's roster on the work. Asking for lead transfers
 * it: the backend demotes whoever holds it in the same transaction. */
export async function addTeamMember(
  firmId: number,
  projectId: number,
  payload: ProjectMemberAdd,
): Promise<ProjectMemberOut> {
  const { data } = await api.post<ProjectMemberOut>(
    teamUrl(firmId, projectId),
    payload,
  );
  return data;
}

export async function changeTeamRole(
  firmId: number,
  projectId: number,
  accountId: number,
  payload: ProjectMemberRoleUpdate,
): Promise<ProjectMemberOut> {
  const { data } = await api.patch<ProjectMemberOut>(
    `${teamUrl(firmId, projectId)}/${accountId}`,
    payload,
  );
  return data;
}

/** Takes someone off the work. A real removal and not a logical one, unlike
 * every other "baja" in this app: an assignment has no state to flip. */
export async function removeTeamMember(
  firmId: number,
  projectId: number,
  accountId: number,
): Promise<void> {
  await api.delete(`${teamUrl(firmId, projectId)}/${accountId}`);
}
