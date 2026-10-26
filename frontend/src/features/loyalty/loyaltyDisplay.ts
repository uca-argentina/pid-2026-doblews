import dayjs from "dayjs";
import type { Level, LevelOut, PointsEntryOut, PointsRule } from "./types";

/** How a level and a points rule read, in one place so the firm's section and
 * each supplier's card cannot word them differently. */

export const LEVEL_LABELS: Record<Level, string> = {
  bronze: "Bronce",
  silver: "Plata",
  gold: "Oro",
  platinum: "Platino",
};

/** Warm as the level climbs, with the firm's own green at the top. "gray" for
 * Plata rather than a blue: the point is that it is the quiet one. */
export const LEVEL_COLORS: Record<Level, string> = {
  bronze: "orange",
  silver: "gray",
  gold: "yellow",
  platinum: "obra",
};

/** Each rule in the words the history uses, as HU-24 asks: "la regla en
 * palabras". The codes stay on the wire; only this file spells them out. */
export const RULE_LABELS: Record<PointsRule, string> = {
  same_material_similar_quantity: "Mismo material, cantidad similar",
  same_material: "Mismo material, otra cantidad",
  same_supplier: "Material nuevo con este proveedor",
  first_purchase: "Primera compra a este proveedor",
};

/** How full the bar is, between the level reached and the next one.
 *
 * Measured from the current level's threshold and not from zero: at Plata with
 * 60 points the bar shows how far 60 is between 50 and 150, which is what
 * "cuánto falta para el próximo" means. Full at the top level, where there is
 * nothing left to reach.
 */
export function levelProgress(level: LevelOut): number {
  if (level.next_level_at === null) return 100;
  const span = level.next_level_at - level.level_from;
  if (span <= 0) return 100;
  return Math.min(
    100,
    Math.max(0, ((level.points - level.level_from) / span) * 100),
  );
}

/** "Faltan 40 puntos para Oro", or that there is nothing above this one. */
export function nextLevelText(level: LevelOut): string {
  if (level.next_level === null || level.points_to_next === null) {
    return "Es el nivel máximo.";
  }
  const points = level.points_to_next;
  const unit = points === 1 ? "punto" : "puntos";
  return `${points} ${unit} para ${LEVEL_LABELS[level.next_level]}.`;
}

/** "como la vez pasada (1.000 u)" — only the two rules that compared something
 * have anything to say here. */
export function comparedText(entry: PointsEntryOut): string | null {
  if (entry.previous_quantity === null) return null;
  return `La vez pasada: ${Number(entry.previous_quantity).toLocaleString("es-AR")} ${entry.unit.abbreviation}`;
}

/** "26/10/2026", the day the points were earned. */
export function formatDay(value: string): string {
  return dayjs(value).format("DD/MM/YYYY");
}
