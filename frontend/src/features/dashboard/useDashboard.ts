import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { projectKeys } from "../projects/useProjects";
import type { DashboardOut } from "./types";

/** Below the work's key, like the planning and the take-off, so editing the
 * work (its start date) refreshes it. Every other section it reads from is
 * written on its own tab, and this refetches whenever the tab is opened. */
export const dashboardKeys = {
  one: (firmId: number, projectId: number) =>
    [...projectKeys.one(firmId, projectId), "dashboard"] as const,
};

/** HU-19: the three blocks of a work's dashboard, in one answer. */
export async function fetchDashboard(
  firmId: number,
  projectId: number,
): Promise<DashboardOut> {
  const { data } = await api.get<DashboardOut>(
    `/firms/${firmId}/projects/${projectId}/dashboard`,
  );
  return data;
}

export function useDashboard(firmId: number, projectId: number) {
  return useQuery({
    queryKey: dashboardKeys.one(firmId, projectId),
    queryFn: () => fetchDashboard(firmId, projectId),
  });
}
