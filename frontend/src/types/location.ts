export type LocationType =
  | "customer_address"
  | "tailor_shop"
  | "vendor_warehouse"
  | "delivery_dropoff"
  | "delivery_pickup";

export interface GeoLocation {
  id: string;
  latitude: number;
  longitude: number;
  location_type: LocationType;
  formatted_address?: string | null;
  city?: string | null;
  state_region?: string | null;
  country?: string | null;
  postal_code?: string | null;
}

export interface Address {
  id: string;
  label?: string | null;
  recipient_name?: string | null;
  recipient_phone?: string | null;
  is_default: boolean;
}
