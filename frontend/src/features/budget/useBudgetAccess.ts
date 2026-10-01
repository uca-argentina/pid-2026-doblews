import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";

/** Whether the caller may see the budget of the work in the URL.
 *
 * Mirrors the backend's requires_any: project.cost.view on the work, or the
 * owner's project.view_all on the firm, which is how they audit a work they
 * are not a member of and so hold no project role on.
 *
 * This is where HU-11 differs from HU-5, and the difference is the point. The
 * take-off hides the costs from the client and still shows them the
 * quantities; here the same permission closes the whole section, so the tab is
 * not rendered for them at all. */
export function useBudgetAccess(): boolean {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return project.can("project.cost.view") || firm.can("project.view_all");
}
