// Mirrors backend/app/schemas/project.py field for field. Kept in the wire's
// own field names (snake_case) on purpose: there is no case-mapping layer
// between the API and the frontend, and adding one would be one more place for
// the two sides to drift apart.

/** The client of a work, or nobody.
 *
 * Nested rather than flattened into client_id/client_name because there either
 * is a client or there is not, and one optional object says that once.
 *
 * There is no project.client_id in the database: the client is a row of
 * project_member with the client role (ADR-002 section 6), which is why the
 * form sends an account id and the listing reads back a name. */
export interface ProjectClientOut {
  account_id: number;
  name: string;
}

/** One row of the listing. Exactly what HU-3 asks it to show, and no
 * description: that is a paragraph and belongs on the detail screen. */
export interface ProjectSummary {
  id: number;
  name: string;
  address: string | null;
  /** A calendar date as "YYYY-MM-DD", with no time and no timezone. The same
   * shape Mantine's DateInput uses, so no conversion is needed either way. */
  estimated_start_date: string | null;
  client: ProjectClientOut | null;
}

/** A work in full. What a write answers with. */
export interface ProjectOut extends ProjectSummary {
  description: string | null;
}

/** What GET /firms/{firmId}/projects/{projectId} returns: the work plus what
 * the caller may do to it.
 *
 * permissions is for painting only — whether to offer "Editar" and "Dar de
 * baja". The backend resolves them again on every request, so a stale copy
 * here can hide a button but never open a door. It is the same contract as
 * FirmDetail.permissions.
 *
 * An empty array is a real answer: the owner of the firm sees every work
 * through project.view_all and holds no role on the ones they are not part of. */
export interface ProjectDetail extends ProjectOut {
  permissions: string[];
}

/** The add and edit form: the whole editable state of a work.
 *
 * One type for both, because the backend has one shape for both and the edit
 * is a PUT: the form sends every field every time, so null means empty rather
 * than "leave it as it was". */
export interface ProjectWrite {
  name: string;
  description: string | null;
  address: string | null;
  estimated_start_date: string | null;
  /** An account id and not an email: the picker is fed by this firm's roster,
   * so the form already holds the id of everyone it may offer. */
  client_account_id: number | null;
}
