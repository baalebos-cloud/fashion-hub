export interface Design {
  id: string;
  title: string;
  description?: string | null;
  base_price: number;
  is_published: boolean;
  // Set by the tailor/designer per design (see
  // backend/docs/measurement-requirements.md) -- null/empty means the
  // customer's own default measurement profile applies as-is.
  required_measurement_fields?: string[] | null;
}

export interface CreateDesignPayload {
  title: string;
  description?: string;
  base_price: number;
  category_id?: string;
  required_measurement_fields?: string[];
}
