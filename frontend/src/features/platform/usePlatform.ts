import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  changeFirmStatus,
  createFirm,
  fetchPlatformFirms,
  resetPassword,
} from "./platformService";
import type { FirmCreate, PasswordReset } from "./types";

/** Query keys for support's screens.
 *
 * Under ["platform"] and not ["firm", id]: these rows are the platform's view
 * of every firm, a different answer from what a member of one firm is shown,
 * and invalidating one must never touch the other's cache. */
export const platformKeys = {
  firms: () => ["platform", "firms"] as const,
};

/** Every firm on the platform, with its head count and state. */
export function usePlatformFirms() {
  return useQuery({
    queryKey: platformKeys.firms(),
    queryFn: fetchPlatformFirms,
  });
}

/** Creates a firm and its owner.
 *
 * Returning the invalidation from onSuccess keeps the mutation pending until
 * the listing has been refetched, so the modal closes onto a list that already
 * shows the new firm — the same pattern as useMembers.ts.
 *
 * Errors are not handled here: the modal renders them next to the form, since
 * a 409 ("una cuenta de soporte no puede ser propietaria") is something support
 * can act on. */
export function useCreateFirm() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: FirmCreate) => createFirm(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: platformKeys.firms() }),
  });
}

/** Suspends or reactivates a firm. */
export function useChangeFirmStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (variables: { firmId: number; isActive: boolean }) =>
      changeFirmStatus(variables.firmId, { is_active: variables.isActive }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: platformKeys.firms() }),
  });
}

/** Resets an account's password. Nothing cached depends on it, so there is
 * nothing to invalidate. */
export function useResetPassword() {
  return useMutation({
    mutationFn: (payload: PasswordReset) => resetPassword(payload),
  });
}
