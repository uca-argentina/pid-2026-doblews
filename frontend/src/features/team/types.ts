// Mirrors backend/app/schemas/project_member.py field for field. Kept in the
// wire's own field names (snake_case) on purpose: there is no case-mapping
// layer between the API and the frontend, and adding one would be one more
// place for the two sides to drift apart.

import type { RoleOut } from "../auth/types";

/** The roles a lead may hand out on a work. Mirrors AssignableProjectRole in
 * backend/app/services/project_team.py, which is the whole project catalogue:
 * unlike the firm roster, where owner is withheld, the work's own responsible
 * is one of these and handing it over is what a transfer is. The API answers
 * 422 to anything else, so this type only catches it before sending. */
export type AssignableProjectRole =
  "lead" | "collaborator" | "viewer" | "client";

/** The project role whose holder answers for the work. Assigning it to someone
 * else transfers it, which is why the UI warns before doing so. */
export const LEAD: AssignableProjectRole = "lead";

/** The project role a firm client is the only one who may hold, and the only
 * one a firm client may be given (ADR-002 section 11.2). */
export const CLIENT: AssignableProjectRole = "client";

export interface ProjectMemberOut {
  account_id: number;
  name: string;
  email: string;
  /** The role on this work, not in the firm: someone can be an architect of
   * the studio and a viewer of this particular work. */
  role: RoleOut;
  /** The state of their roster row, not of the assignment. False means they
   * left the firm: the seat is still theirs and comes back with them, and
   * until then it grants nothing (ADR-002 section 11.3). */
  is_active: boolean;
  joined_at: string;
}

export interface ProjectMemberAdd {
  account_id: number;
  role_code: AssignableProjectRole;
}

export interface ProjectMemberRoleUpdate {
  role_code: AssignableProjectRole;
}
