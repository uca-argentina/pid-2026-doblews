import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";

/** Whether the caller may see what the work in the URL costs: the live budget
 * on the take-off, and the budgets saved from it.
 *
 * Mirrors the backend's requires_any: project.cost.view on the work, or the
 * owner's project.view_all on the firm, which is how they audit a work they
 * are not a member of and so hold no project role on.
 *
 * The two places answer it differently, and the difference is the point. The
 * take-off still opens for the client and shows them the quantities with no
 * money on them; the saved budgets are nothing but money, so the same
 * permission closes the whole tab and it is not rendered for them at all. */
export function useBudgetAccess(): boolean {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return project.can("project.cost.view") || firm.can("project.view_all");
}
