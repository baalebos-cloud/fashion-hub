export interface Vendor {
  id: string;
  user_id: string;
  business_name: string;
  business_description?: string | null;
  is_verified: boolean;
  average_rating: number;
  /** Set once the vendor saves a store pickup point; required before requesting riders. */
  warehouse_location_id?: string | null;
}
