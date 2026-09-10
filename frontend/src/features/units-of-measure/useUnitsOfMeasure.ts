import { useQuery } from "@tanstack/react-query";
import { fetchUnitsOfMeasure } from "./unitOfMeasureService";

/** The unit of measure catalogue, ready for any "unidad" <Select> (HU-0).
 *
 * staleTime: Infinity because it is a closed catalogue seeded by migration —
 * it cannot change during a session, so there is nothing to refetch. Shared
 * across every consumer via the query cache, so the first form to render a
 * unit select pays the request and the rest read the cache. */
export function useUnitsOfMeasure() {
  return useQuery({
    queryKey: ["units-of-measure"],
    queryFn: fetchUnitsOfMeasure,
    staleTime: Infinity,
  });
}
