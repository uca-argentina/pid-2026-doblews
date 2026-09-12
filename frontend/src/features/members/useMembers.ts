import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addMember, fetchMemberRoles, fetchMembers } from "./memberService";
import type { MemberCreate } from "./types";

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

/** Adds someone to the roster, or brings back someone who left.
 *
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the roster has actually been refetched, so the modal closes onto a list that
 * already shows the change instead of onto the old one.
 *
 * Errors are not handled here: each modal renders them itself, because a 409
 * is something the person can act on and belongs next to the form they were
 * filling in. */
export function useAddMember(firmId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: MemberCreate) => addMember(firmId, payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: memberKeys.all(firmId) }),
  });
}
