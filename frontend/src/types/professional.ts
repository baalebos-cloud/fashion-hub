export type ProfessionalType = "tailor" | "designer";

export interface Professional {
  id: string;
  user_id: string;
  professional_type: ProfessionalType;
  business_name?: string | null;
  bio?: string | null;
  years_experience?: number | null;
  shop_photo_url?: string | null;
  is_verified: boolean;
  average_rating: number;
  review_count: number;
  accepts_new_orders: boolean;
}
