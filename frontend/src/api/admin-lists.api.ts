import { apiClient } from "@/lib/api/client";

/** Read-only admin lists and reports (backend/app/api/v1/admin_lists.py). */
export interface Paged<T> { total: number; page: number; page_size: number; items: T[] }
export type ListParams = Record<string, string | number | boolean | undefined>;

export interface AdminVendor { id: string; business_name: string; owner_name: string | null; owner_email: string | null;
  is_verified: boolean; average_rating: number; active_products: number; created_at: string | null }
export interface AdminRider { id: string; name: string | null; email: string | null; vehicle_type: string | null;
  is_verified: boolean; is_available: boolean; average_rating: number; completed_deliveries: number; created_at: string | null }
export interface AdminPayment { id: string; order_id: string; order_number: string; order_type: string; buyer_name: string | null;
  amount: number; currency: string; provider: string; status: string; reference: string; paid_at: string | null; created_at: string | null }
export interface AdminInvoice { id: string; invoice_number: string; order_id: string; issued_to: string | null; issued_by: string | null;
  total_amount: number; currency: string; payment_status: string; order_date: string | null; payment_date: string | null }
export interface AdminReview { id: string; order_number: string | null; reviewer: string | null; reviewee: string | null;
  score: number | null; comment: string | null; created_at: string | null }
interface OrderFigures { placed: number; paid: number; completed: number; cancelled: number; gmv: number }
interface Funnel { submitted: number; verified: number; rejected: number; waiting: number }
export interface AdminReports { days: number; currency: string; gmv: number; garment_orders: OrderFigures; material_orders: OrderFigures;
  orders_per_day: { date: string; orders: number }[]; identity_checks: Funnel; business_checks: Funnel }

const list = <T,>(path: string) => async (params: ListParams = {}): Promise<Paged<T>> =>
  (await apiClient.get<Paged<T>>(`/admin/${path}`, { params })).data;

export const adminListsApi = {
  vendors: list<AdminVendor>("vendors"),
  riders: list<AdminRider>("delivery-partners"),
  payments: list<AdminPayment>("payments"),
  invoices: list<AdminInvoice>("invoices"),
  reviews: list<AdminReview>("reviews"),
  async reports(days = 30): Promise<AdminReports> {
    return (await apiClient.get<AdminReports>("/admin/reports", { params: { days } })).data;
  },
};
