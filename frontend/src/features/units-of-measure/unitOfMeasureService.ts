import { api } from "../../lib/api";
import type { UnitOfMeasureOut } from "./types";

export async function fetchUnitsOfMeasure(): Promise<UnitOfMeasureOut[]> {
  const { data } = await api.get<UnitOfMeasureOut[]>("/units-of-measure");
  return data;
}
