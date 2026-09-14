export interface TrackingSnapshot {
  delivery_id: string;
  current_latitude?: number | null;
  current_longitude?: number | null;
  current_status: string;
  eta_minutes?: number | null;
}

export interface OrderTrackingResponse {
  order_id: string;
  status: string;
  tracking: TrackingSnapshot | null;
}
