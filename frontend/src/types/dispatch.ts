import type { RouteSummary } from "@/lib/utils/route";

export interface MyOffer {
  id: string;
  amount: number;
  status: "pending" | "accepted" | "declined" | "withdrawn";
  eta_to_pickup_minutes: number;
  expires_at: string;
}

/** What a rider sees before claiming: areas only, never exact addresses or contacts. */
export interface DispatchJob {
  id: string;
  order_id: string;
  status: string;
  suggested_fare: number;
  currency: string;
  offer_min: number;
  offer_max: number;
  approx_road_km: number | null;
  route?: RouteSummary | null;
  pickup_area: string | null;
  dropoff_area: string | null;
  posted_at: string;
  my_offer: MyOffer | null;
}

export interface RiderCardInfo {
  first_name: string;
  is_verified: boolean;
  rating: number;
  vehicle_type: string | null;
  completed_deliveries: number;
  photo_url: string | null;
}

export interface SellerOffer {
  id: string;
  amount: number;
  eta_to_pickup_minutes: number;
  expires_at: string;
  rider: RiderCardInfo;
}

export interface SellerDispatchView {
  request: { id: string; status: string; suggested_fare: number; approx_road_km: number | null; currency: string; route?: RouteSummary | null } | null;
  offers: SellerOffer[];
}

export interface JourneyMilestone {
  key: string;
  label: string;
  at: string | null;
  state: "done" | "current" | "upcoming";
}

export interface DeliveryJourney {
  order_id: string;
  tracking_number: string;
  status: string;
  delivery_status: string | null;
  milestones: JourneyMilestone[];
  live: { eta_minutes: number | null; distance_remaining_km: number | null; basis: "live_gps_estimate" | "road_route"; traffic_aware?: boolean; updated_at: string | null } | null;
  /** Vendor -> tailor material orders feeding a customer order. Never prices or addresses. */
  materials_legs?: MaterialsLeg[];
}

export interface MaterialsLeg {
  order_id: string;
  vendor_name: string;
  status: string;
  label: string;
  done: boolean;
  updated_at: string | null;
}

/** A job Tailora reserved for this rider (auto-dispatch) until expires_at. */
export interface ReservedJob {
  id: string;
  expires_at: string;
  attempt: number;
  job: DispatchJob;
}
