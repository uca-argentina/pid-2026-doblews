/** The three kinds of resource a recipe yields, and what a work's screens call
 * them when they group by kind.
 *
 * Shared because the take-off and the budget have to agree: the same hours
 * cannot sit under "Mano de obra" on one screen and "Labor" on the other.
 * Plural on purpose — these are section headings, not the singular type label
 * the catalogue shows on a resource's own row.
 *
 * The order is the one the backend sends and the screens render: what the work
 * is built of, who builds it, what they build it with. */

export type ResourceType = "material" | "labor" | "equipment";

export const RESOURCE_TYPES: readonly ResourceType[] = [
  "material",
  "labor",
  "equipment",
] as const;

export const RESOURCE_GROUP_LABELS: Record<ResourceType, string> = {
  material: "Materiales",
  labor: "Mano de obra",
  equipment: "Equipos",
};
