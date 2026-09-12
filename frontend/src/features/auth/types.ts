// Mirrors backend/app/schemas/{auth,firm}.py field for field. Kept in the
// wire's own field names (snake_case) on purpose: there is no case-mapping
// layer between the API and the frontend, and adding one would be one more
// place for the two sides to drift apart.

export interface RoleOut {
  code: string;
  name: string;
}

export interface FirmSummary {
  id: number;
  name: string;
  role: RoleOut;
}

/** What GET /firms/{id} returns: the firm plus what the caller may do in it.
 *
 * permissions is for painting only — which sections and buttons to show. The
 * backend resolves them again on every request, so a stale copy here can hide
 * a button but never open a door. */
export interface FirmDetail extends FirmSummary {
  permissions: string[];
}

export interface MeResponse {
  id: number;
  name: string;
  email: string;
  platform_roles: string[];
  firms: FirmSummary[];
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}
