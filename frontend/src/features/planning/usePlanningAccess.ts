import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";

export interface PlanningAccess {
  /** May open the planning tab at all. */
  canView: boolean;
  /** May create, edit and remove tasks, change their status and assign
   * take-off lines to them. */
  canManage: boolean;
}

/** What the caller may do with the planning of the work in the URL.
 *
 * The same two heights as useTakeoffAccess, mirroring the backend's
 * requires_any: reading is granted on the work, through project.task.view, or
 * on the firm, through the owner's project.view_all. Writing has one height
 * only: view_all opens the reading, never the writing.
 *
 * Whether costs are shown is not decided here. The backend already withholds
 * them from whoever may not see them, so the screen reads total_cost instead
 * of repeating that rule. */
export function usePlanningAccess(): PlanningAccess {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return {
    canView: project.can("project.task.view") || firm.can("project.view_all"),
    canManage: project.can("project.task.manage"),
  };
}
