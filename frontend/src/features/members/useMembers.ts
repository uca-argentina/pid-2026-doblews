import { useQuery } from "@tanstack/react-query";
import { fetchMemberRoles, fetchMembers } from "./memberService";

/** Query keys for everything about one firm's roster.
 *
 * They hang under ["firm", firmId], the key FirmLayout already uses, so a
 * mutation can invalidate exactly this firm's roster and nothing else. */
export const memberKeys = {
  all: (firmId: number) => ["firm", firmId, "members"] as const,
  roles: (firmId: number) => ["firm", firmId, "member-roles"] as const,
};

/** The roster of the active firm, active and inactive alike. */
export function useMembers(firmId: number) {
  return useQuery({
    queryKey: memberKeys.all(firmId),
    queryFn: () => fetchMembers(firmId),
  });
}

/** The options of every "rol" <Select> in this section.
 *
 * staleTime: Infinity because the role catalogue is seeded by migration and
 * cannot change during a session — the same reasoning as useUnitsOfMeasure.
 * Shared through the query cache, so the add and the edit forms fetch it once
 * between them. */
export function useMemberRoles(firmId: number) {
  return useQuery({
    queryKey: memberKeys.roles(firmId),
    queryFn: () => fetchMemberRoles(firmId),
    staleTime: Infinity,
  });
}
