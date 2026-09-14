import { api } from "../../lib/api";
import type {
  TakeoffLineCreate,
  TakeoffLineOut,
  TakeoffLineUpdate,
  TakeoffOut,
} from "./types";

/** Every call HU-5's screen makes. One module so the URLs live in one place,
 * and the hooks in useTakeoff.ts stay about caching. */

function takeoffUrl(firmId: number, projectId: number): string {
  return `/firms/${firmId}/projects/${projectId}/takeoff`;
}

/** The whole take-off of a work: its lines, its materials and — for those who
 * may see it — what they cost. */
export async function fetchTakeoff(
  firmId: number,
  projectId: number,
): Promise<TakeoffOut> {
  const { data } = await api.get<TakeoffOut>(takeoffUrl(firmId, projectId));
  return data;
}

/** Loads a recipe onto the work. A 409 means the recipe was retired from the
 * catalogue while the form was open, and its detail says what to do. */
export async function createLine(
  firmId: number,
  projectId: number,
  payload: TakeoffLineCreate,
): Promise<TakeoffLineOut> {
  const { data } = await api.post<TakeoffLineOut>(
    `${takeoffUrl(firmId, projectId)}/lines`,
    payload,
  );
  return data;
}

/** A PUT: the quantity and the note are both sent, so an empty note clears it. */
export async function updateLine(
  firmId: number,
  projectId: number,
  lineId: number,
  payload: TakeoffLineUpdate,
): Promise<TakeoffLineOut> {
  const { data } = await api.put<TakeoffLineOut>(
    `${takeoffUrl(firmId, projectId)}/lines/${lineId}`,
    payload,
  );
  return data;
}

/** A logical removal: the API answers 204 and the line's materials stop adding
 * up at once. */
export async function removeLine(
  firmId: number,
  projectId: number,
  lineId: number,
): Promise<void> {
  await api.delete(`${takeoffUrl(firmId, projectId)}/lines/${lineId}`);
}
