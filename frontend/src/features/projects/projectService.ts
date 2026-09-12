import { api } from "../../lib/api";
import type {
  ProjectDetail,
  ProjectOut,
  ProjectSummary,
  ProjectWrite,
} from "./types";

/** Every call the project screens make. One module so the URLs live in one
 * place, and the hooks in useProjects.ts stay about caching. */

function projectsUrl(firmId: number): string {
  return `/firms/${firmId}/projects`;
}

/** The works of this firm the caller may see: the ones they are on, or all of
 * them when they hold project.view_all. Which ones is the backend's answer,
 * never a filter applied here. */
export async function fetchProjects(firmId: number): Promise<ProjectSummary[]> {
  const { data } = await api.get<ProjectSummary[]>(projectsUrl(firmId));
  return data;
}

/** One work, with what the caller may do to it. A work that is not theirs
 * answers 404, exactly like one that does not exist (HU-3), so the only error
 * the screen has to explain is "not found". */
export async function fetchProject(
  firmId: number,
  projectId: number,
): Promise<ProjectDetail> {
  const { data } = await api.get<ProjectDetail>(
    `${projectsUrl(firmId)}/${projectId}`,
  );
  return data;
}

/** Creates a work and puts the caller on it as its lead, in one transaction:
 * without that they would create something they cannot see. */
export async function createProject(
  firmId: number,
  payload: ProjectWrite,
): Promise<ProjectOut> {
  const { data } = await api.post<ProjectOut>(projectsUrl(firmId), payload);
  return data;
}

/** A PUT and not a PATCH: the form sends the whole work, so a field left empty
 * is cleared rather than left alone. The client follows the same rule. */
export async function updateProject(
  firmId: number,
  projectId: number,
  payload: ProjectWrite,
): Promise<ProjectOut> {
  const { data } = await api.put<ProjectOut>(
    `${projectsUrl(firmId)}/${projectId}`,
    payload,
  );
  return data;
}

/** A logical removal: the API answers 204, the work leaves the listing and its
 * detail answers 404 from then on. Nothing is deleted, and the team stays
 * assigned. */
export async function archiveProject(
  firmId: number,
  projectId: number,
): Promise<void> {
  await api.delete(`${projectsUrl(firmId)}/${projectId}`);
}
