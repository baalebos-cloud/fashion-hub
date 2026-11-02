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
  proof_of_delivery_url?: string | null;
  rider_name?: string | null;
  rider_phone?: string | null;
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
  contact_name: string | null;
  contact_phone: string | null;
}

export interface DeliveryTrip extends Delivery {
  pickup: DispatchWaypoint;
  dropoff: DispatchWaypoint;
  straight_line_km: number | null;
  distance_source: "haversine";
}
