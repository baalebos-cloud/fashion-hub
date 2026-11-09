export type LocationType =
  | "customer_address"
  | "tailor_shop"
  | "vendor_warehouse"
  | "delivery_dropoff"
  | "delivery_pickup";

/** A point chosen on the map, with whatever address parts were found for it. */
export interface PickedLocation {
  latitude: number;
  longitude: number;
  formatted_address?: string | null;
  city?: string | null;
  state_region?: string | null;
  country?: string | null;
  street?: string | null;
  area?: string | null;
  lga?: string | null;
  landmark?: string | null;
  nearest_bus_stop?: string | null;
}

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
