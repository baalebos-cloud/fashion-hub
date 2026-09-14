import type { User, UserRole } from "@/types/user";

/**
 * IMPORTANT: these checks control what the UI *shows* (which buttons
 * render, which nav items appear) — they are not a security boundary.
 * The backend re-checks role AND ownership on every request regardless of
 * what the frontend decided to display (see backend/docs/security.md).
 * Never let a frontend-only check be the sole guard around a sensitive
 * action; it's a UX affordance, not authorization.
 */

export function hasRole(user: User | null, ...roles: UserRole[]): boolean {
  if (!user) return false;
  return roles.includes(user.role);
}

export function isCustomer(user: User | null): boolean {
  return hasRole(user, "customer");
}

export function isProfessional(user: User | null): boolean {
  return hasRole(user, "tailor", "designer");
}

export function isVendor(user: User | null): boolean {
  return hasRole(user, "vendor");
}

export function isDeliveryPartner(user: User | null): boolean {
  return hasRole(user, "delivery_partner");
}

export function isAdmin(user: User | null): boolean {
  return hasRole(user, "admin");
}

/** Only the order's own BUYER may mark it received — a customer on a
 * customer_order, or a tailor/designer (as the buyer) on a vendor_order
 * they placed with a vendor. Mirrors backend/app/services/order_service.py
 * exactly: ownership by user ID, not role, is the actual rule. A role
 * check alone (e.g. "must be a customer") would incorrectly hide this
 * button from a professional confirming receipt of their own vendor
 * materials order — again, cosmetic here only; the backend independently
 * enforces the same buyer_user_id check on every request. */
export function canMarkOrderReceived(user: User | null, order: { status: string; buyer_user_id: string }): boolean {
  if (!user) return false;
  return user.id === order.buyer_user_id && order.status === "delivered";
}
