import { useCurrentFirm } from "../firms/firmContext";
import { useCurrentProject } from "../projects/projectContext";

/** Whether the caller may see what the work in the URL costs right now: the
 * live budget on the take-off, the cost of its tasks, the dashboard and the
 * purchasing comparison.
 *
 * Mirrors the backend's requires_any: project.cost.view on the work, or the
 * owner's project.view_all on the firm, which is how they audit a work they
 * are not a member of and so hold no project role on.
 *
 * This is the internal number, the one that moves while the architect edits.
 * The client of the work does not see it, which is why the take-off opens for
 * them with the quantities and no money on them. What they do see is the hook
 * below. */
export function useBudgetAccess(): boolean {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return project.can("project.cost.view") || firm.can("project.view_all");
}

/** Whether the caller may see the budgets this work has saved (HU-25).
 *
 * A separate question from the one above since ADR-013 section 1, and the
 * separation is the whole story: a saved version is not an internal cost but
 * the budget the studio froze in order to present it, so the client reads it
 * while everything the first hook guards stays closed to them.
 *
 * Mirrors that route's guard, which moved with it: project.budget_version.view
 * on the work, or the owner's project.view_all. lead and collaborator hold the
 * new permission too, so for them nothing changed. */
export function useBudgetVersionAccess(): boolean {
  const firm = useCurrentFirm();
  const project = useCurrentProject();

  return (
    project.can("project.budget_version.view") || firm.can("project.view_all")
  );
}
