// Mirrors backend/app/schemas/platform.py field for field. Kept in the wire's
// own field names (snake_case) on purpose: there is no case-mapping layer
// between the API and the frontend, and adding one would be one more place for
// the two sides to drift apart.

/** One row of support's firm listing. A head count and no members: who works
 * in a firm is its owner's business (ADR-002 section 7). */
export interface FirmAdminOut {
  id: number;
  name: string;
  contact_email: string;
  phone: string | null;
  /** false means suspended: nobody on its roster can act in it. */
  is_active: boolean;
  /** Active roster rows only. */
  member_count: number;
  created_at: string;
}

/** The owner as stored, which is not always as typed: when the address
 * already had an account, name and password are that person's own. */
export interface OwnerOut {
  account_id: number;
  name: string;
  email: string;
  /** true when the address already had an account: the typed password was
   * ignored and is not the one to hand over. */
  account_existed: boolean;
}

export interface FirmCreatedOut extends FirmAdminOut {
  owner: OwnerOut;
}

export interface OwnerCreate {
  name: string;
  email: string;
  password: string;
}

/** The firm and its first owner travel in one body: ADR-002 section 10 does
 * not allow a firm without an owner, not even between two requests. */
export interface FirmCreate {
  name: string;
  contact_email: string;
  /** "" is fine: the backend stores a blank phone as null. */
  phone: string;
  owner: OwnerCreate;
}

export interface FirmStatusUpdate {
  is_active: boolean;
}

export interface PasswordReset {
  email: string;
  password: string;
}
