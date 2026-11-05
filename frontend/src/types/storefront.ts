export type StorefrontKind = "tailor" | "designer" | "vendor";

export interface StorefrontLink {
  handle: string;
  share_url: string;
  is_public: boolean;
  status_message: string;
}

export interface StorefrontReview {
  id: string;
  reviewer_first_name: string;
  score: number | null;
  comment: string | null;
  created_at: string;
}

export interface StorefrontDesign {
  id: string;
  title: string;
  base_price: number;
  currency: string;
  estimated_turnaround_days: number | null;
}

export interface StorefrontProduct {
  id: string;
  name: string;
  base_price: number;
  currency: string;
  unit_of_measure: string;
  image_url: string | null;
}

export interface Storefront {
  handle: string;
  share_url: string;
  kind: StorefrontKind;
  professional_id?: string;
  vendor_id?: string;
  display_name: string;
  bio: string | null;
  is_verified: boolean;
  average_rating: number;
  review_count: number;
  years_experience: number | null;
  accepts_new_orders: boolean;
  area: string | null;
  member_since: number | null;
  profile_photo_url: string | null;
  designs: StorefrontDesign[];
  products: StorefrontProduct[];
  portfolio: { id: string; image_url: string }[];
  reviews: StorefrontReview[];
}
