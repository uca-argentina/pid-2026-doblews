import { api } from "../../lib/api";
import type { RoleOut } from "../auth/types";
import type { MemberCreate, MemberOut, MemberRoleUpdate } from "./types";

/** Every call the roster screen makes. One module so the URLs live in one
 * place, and the hooks in useMembers.ts stay about caching. */

function membersUrl(firmId: number): string {
  return `/firms/${firmId}/members`;
}

/** The whole roster, the people who left included: HU-2 lists them with their
 * state, and that listing is where the owner finds someone to bring back. */
export async function fetchMembers(firmId: number): Promise<MemberOut[]> {
  const { data } = await api.get<MemberOut[]>(membersUrl(firmId));
  return data;
}

/** The roles the add and edit forms offer: architect and client, never owner.
 * Read from the API so the labels are the seeded ones ("Arquitecto",
 * "Cliente") and this app keeps no dictionary of its own. */
export async function fetchMemberRoles(firmId: number): Promise<RoleOut[]> {
  const { data } = await api.get<RoleOut[]>(`${membersUrl(firmId)}/roles`);
  return data;
}

/** Adds someone to the roster, and also brings back someone who left: the
 * backend answers both with the same 201 and the member as stored. */
export async function addMember(
  firmId: number,
  payload: MemberCreate,
): Promise<MemberOut> {
  const { data } = await api.post<MemberOut>(membersUrl(firmId), payload);
  return data;
}

export async function changeMemberRole(
  firmId: number,
  accountId: number,
  payload: MemberRoleUpdate,
): Promise<MemberOut> {
  const { data } = await api.patch<MemberOut>(
    `${membersUrl(firmId)}/${accountId}`,
    payload,
  );
  return data;
}

/** A logical removal: the API answers 204 and the person shows up as inactive
 * from then on. Nothing is deleted, so their projects wait for them. */
export async function removeMember(
  firmId: number,
  accountId: number,
): Promise<void> {
  await api.delete(`${membersUrl(firmId)}/${accountId}`);
}
