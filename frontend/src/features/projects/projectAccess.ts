/** Whether the caller only follows works and never runs them: no
 * project.create and no project.view_all in the firm (ADR-013 section 3).
 *
 * Who meets it gets "Mis obras" instead of the listing. A rule of permissions
 * and not "is a client": today only the client meets it, and a read-only role
 * added later would fall in the same view without touching this. */
export function seesOnlyOwnProjects(
  can: (permission: string) => boolean,
): boolean {
  return !can("project.create") && !can("project.view_all");
}
