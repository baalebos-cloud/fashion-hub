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
}

export interface DeliveryPartner {
  id: string;
  vehicle_type?: string | null;
  is_verified: boolean;
  is_available: boolean;
  average_rating: number;
}
