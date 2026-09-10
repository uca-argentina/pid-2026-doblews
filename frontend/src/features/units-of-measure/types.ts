// Mirrors backend/app/schemas/unit_of_measure.py field for field. Kept in the
// wire's own field names (snake_case) on purpose: there is no case-mapping
// layer between the API and the frontend, and adding one would be one more
// place for the two sides to drift apart.

export interface UnitOfMeasureOut {
  id: number;
  code: string;
  name: string;
  abbreviation: string;
  magnitude: string;
}
