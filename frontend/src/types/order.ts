/**
 * Mirrors backend/app/core/constants.py — keep these two files in sync.
 * The full valid-transition map is intentionally NOT duplicated here: the
 * backend is the single source of truth for what transitions are legal.
 * The frontend only needs to know which statuses exist, to render badges
 * and decide which action buttons to *show* — the backend independently
 * re-validates every transition regardless of what the UI displays.
 */
export type CustomerOrderStatus =
  | "pending"
  | "paid"
  | "accepted"
  | "in_production"
  | "ready_for_delivery"
  | "shipped"
  | "out_for_delivery"
  | "delivered"
  | "received"
  | "completed"
  | "cancelled"
  | "rejected"
  | "refunded";

export type VendorOrderStatus =
  | "cart"
  | "checkout"
  | "payment_pending"
  | "paid"
  | "confirmed"
  | "processing"
  | "ready_for_pickup"
  | "picked_up"
  | "in_transit"
  | "delivered"
  | "received"
  | "completed"
  | "cancelled"
  | "refunded";

export type OrderType = "customer_order" | "vendor_order";

export interface OrderItem {
  id: string;
  reference_type: string;
  name_snapshot: string;
  unit_price: number;
  quantity: number;
  line_total: number;
}

export interface Order {
  id: string;
  order_number: string;
  order_type: OrderType;
  status: CustomerOrderStatus | VendorOrderStatus;
  buyer_user_id: string;
  seller_user_id: string;
  subtotal: number;
  delivery_fee: number;
  tax_amount: number;
  discount_amount: number;
  total_amount: number;
  currency: string;
  ordered_at?: string | null;
  paid_at?: string | null;
  accepted_at?: string | null;
  production_started_at?: string | null;
  ready_at?: string | null;
  shipped_at?: string | null;
  out_for_delivery_at?: string | null;
  delivered_at?: string | null;
  received_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
}

export interface OrderTimelineEntry {
  from_status: string | null;
  to_status: string;
  actor_user_id: string | null;
  note: string | null;
  created_at: string;
}

export interface CreateCustomerOrderPayload {
  professional_user_id: string;
  items: Array<{
    reference_type: string;
    reference_id?: string;
    name_snapshot: string;
    unit_price: number;
    quantity: number;
  }>;
  delivery_address_id: string;
  measurement_profile_id?: string;
  idempotency_key?: string;
}
