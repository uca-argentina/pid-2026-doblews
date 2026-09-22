import { createContext, useContext } from "react";
import type { ProjectDetail } from "./types";

export interface CurrentProject {
  project: ProjectDetail;
  /** Whether the caller holds a project permission on this work, e.g.
   * can("project.edit").
   *
   * The same question the firm context answers one level up, and asked the
   * same way: never "what is my role in this work?", per ADR-002 — roles are
   * data, permissions are what the code checks. The backend asks it again on
   * every request, so a stale answer here can hide a button and never open a
   * door.
   *
   * It is a different set from the firm's: project.create lives on the firm
   * (there is no work yet to hang it off), while project.edit and
   * project.archive only exist inside one. */
  can: (permission: string) => boolean;
}

/** Provided by ProjectLayout, which has already resolved the work from the URL.
 *
 * A .ts file with no components on purpose: react-refresh can only hot-reload
 * files that export components alone, so the provider lives in ProjectLayout —
 * the same split as firmContext.ts and FirmLayout. */
export const ProjectContext = createContext<CurrentProject | null>(null);

/** The work in the URL, for any screen under /firms/:firmId/projects/:projectId.
 *
 * Never null inside those screens: ProjectLayout renders them only once the
 * work has loaded, and sends the caller back to the listing otherwise. HU-6's
 * team section and HU-5's take-off will read the work from here rather than
 * fetching it again. */
export function useCurrentProject(): CurrentProject {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error(
      "useCurrentProject must be used inside a /firms/:firmId/projects/:projectId route",
    );
  }
  return context;
}
