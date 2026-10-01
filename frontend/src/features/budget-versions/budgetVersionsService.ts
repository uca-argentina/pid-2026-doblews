import { api } from "../../lib/api";
import type {
  BudgetVersionCreate,
  BudgetVersionLoadOut,
  BudgetVersionOut,
  BudgetVersionSummary,
} from "./types";

/** Every call HU-12's screens make. One module so the URLs live in one place,
 * and the hooks stay about caching. */

function versionsUrl(firmId: number, projectId: number): string {
  return `/firms/${firmId}/projects/${projectId}/budget/versions`;
}

/** The versions of a work, newest first. */
export async function fetchVersions(
  firmId: number,
  projectId: number,
): Promise<BudgetVersionSummary[]> {
  const { data } = await api.get<BudgetVersionSummary[]>(
    versionsUrl(firmId, projectId),
  );
  return data;
}

/** One saved version in full. */
export async function fetchVersion(
  firmId: number,
  projectId: number,
  versionId: number,
): Promise<BudgetVersionOut> {
  const { data } = await api.get<BudgetVersionOut>(
    `${versionsUrl(firmId, projectId)}/${versionId}`,
  );
  return data;
}

/** Freeze the budget as it stands. A 409 means the take-off is empty — its last
 * line was removed while the form was open. */
export async function saveVersion(
  firmId: number,
  projectId: number,
  payload: BudgetVersionCreate,
): Promise<BudgetVersionOut> {
  const { data } = await api.post<BudgetVersionOut>(
    versionsUrl(firmId, projectId),
    payload,
  );
  return data;
}

/** Replace the draft's lines with this version's, at today's prices. The answer
 * says how many came back and which were left out. */
export async function loadVersion(
  firmId: number,
  projectId: number,
  versionId: number,
): Promise<BudgetVersionLoadOut> {
  const { data } = await api.post<BudgetVersionLoadOut>(
    `${versionsUrl(firmId, projectId)}/${versionId}/load`,
    {},
  );
  return data;
}
