export interface Design {
  professional_id: string;
  currency: string;
  id: string;
  title: string;
  description?: string | null;
  base_price: number;
  is_published: boolean;
  image_url?: string | null;
  // Set by the tailor/designer per design (see
  // backend/docs/measurement-requirements.md) -- null/empty means the
  // customer's own default measurement profile applies as-is.
  required_measurement_fields?: string[] | null;
}

export interface CreateDesignPayload {
  image_url?: string;
  title: string;
  description?: string;
  base_price: number;
  category_id?: string;
  required_measurement_fields?: string[];
}
