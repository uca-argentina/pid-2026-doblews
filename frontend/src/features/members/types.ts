// Mirrors backend/app/schemas/member.py field for field. Kept in the wire's own
// field names (snake_case) on purpose: there is no case-mapping layer between
// the API and the frontend, and adding one would be one more place for the two
// sides to drift apart.

import type { RoleOut } from "../auth/types";

/** The firm roles an owner may hand out. Mirrors AssignableFirmRole in
 * backend/app/services/roster.py: owner is missing from both, because a second
 * owner would break "exactly one active owner per firm". The API answers 422
 * to anything else, so this type is only there to catch it before sending. */
export type AssignableFirmRole = "architect" | "client";

export interface MemberOut {
  account_id: number;
  name: string;
  email: string;
  role: RoleOut;
  /** Roster state, not account state: false means they left this firm and can
   * still log in and work in any other one. */
  is_active: boolean;
  joined_at: string;
}

export interface MemberCreate {
  name: string;
  email: string;
  role_code: AssignableFirmRole;
  password: string;
}

export interface MemberRoleUpdate {
  role_code: AssignableFirmRole;
}
