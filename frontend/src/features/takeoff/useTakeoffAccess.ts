import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";

export interface TakeoffAccess {
  /** May open the take-off tab at all. */
  canView: boolean;
  /** May add, edit and remove lines. */
  canManage: boolean;
}

/** What the caller may do with the take-off of the work in the URL.
 *
 * Reading is granted at two heights, mirroring the backend's requires_any: on
 * the work, through project.recipe.view, or on the firm, through the owner's
 * project.view_all. The second one matters because the owner opens every work
 * of their firm and holds no role — so an empty permissions list — on the ones
 * they are not part of (ADR-003 section 8). Checking only the work would hide
 * the tab from exactly the person auditing it.
 *
 * Writing has one height only: view_all opens the reading, never the writing.
 *
 * Whether costs are shown is not decided here: that is useBudgetAccess, the
 * rule of the budget the take-off's screen shows next to its lines. */
export function useTakeoffAccess(): TakeoffAccess {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return {
    canView: project.can("project.recipe.view") || firm.can("project.view_all"),
    canManage: project.can("project.recipe.manage"),
  };
}
