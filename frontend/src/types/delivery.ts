export type DeliveryStatus =
  | "requested"
  | "assigned"
  | "rejected"
  | "picked_up"
  | "in_transit"
  | "out_for_delivery"
  | "delivered"
  | "failed"
  | "cancelled";

export interface Delivery {
  id: string;
  order_id: string;
  status: DeliveryStatus;
  delivery_fee: number;
  /** Packages the rider confirmed at pickup. */
  package_count?: number | null;
  /** False while the pickup-code rollout flag is off: the rider skips the code. */
  pickup_code_required?: boolean;
  proof_of_delivery_url?: string | null;
  rider_name?: string | null;
  rider_verified?: boolean | null;
  rider_rating?: number | null;
  rider_vehicle_type?: string | null;
  rider_completed_deliveries?: number | null;
  rider_photo_url?: string | null;
}

export interface HandoverCode {
  delivery_id: string;
  handover_code: string;
  expires_at: string;
  package_count: number | null;
}

export interface PickupCode {
  delivery_id: string;
  required: boolean;
  pickup_code: string | null;
  expires_at: string | null;
}

export interface DeliveryPartner {
  id: string;
  vehicle_type?: string | null;
  is_verified: boolean;
  is_available: boolean;
  average_rating: number;
}

export interface DispatchWaypoint {
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  lga?: string | null;
  landmark?: string | null;
  nearest_bus_stop?: string | null;
  delivery_instructions?: string | null;
  contact_name: string | null;
  /** Whether this stop can be reached through a masked in-app call. */
  can_call: boolean;
}

export interface DeliveryTrip extends Delivery {
  pickup: DispatchWaypoint;
  dropoff: DispatchWaypoint;
  straight_line_km: number | null;
  route?: import("@/lib/utils/route").RouteSummary | null;
  distance_source: "haversine";
}

/** Position is ephemeral and only shared with parties to an active delivery. */
export interface RiderPosition {
  latitude: number;
  longitude: number;
  accuracy_m: number;
  recorded_at: string;
  /** live | delayed | last_known. A last_known point is "last seen", never the current position. */
  freshness?: "live" | "delayed" | "last_known" | null;
  age_seconds?: number | null;
  accepted?: boolean | null;
  device_state?: string | null;
}
