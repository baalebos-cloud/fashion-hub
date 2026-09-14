import type { UserRole } from "@/types/auth";

export const ROLES: Record<string, UserRole> = {
  CUSTOMER: "customer",
  TAILOR: "tailor",
  DESIGNER: "designer",
  VENDOR: "vendor",
  DELIVERY_PARTNER: "delivery_partner",
  ADMIN: "admin",
};

export const ROLE_LABELS: Record<UserRole, string> = {
  customer: "Customer",
  tailor: "Tailor",
  designer: "Fashion Designer",
  vendor: "Vendor",
  delivery_partner: "Delivery Partner",
  admin: "Admin",
};

/** Where each role lands immediately after login — see router/index.tsx. */
export const ROLE_HOME_PATH: Record<UserRole, string> = {
  customer: "/app/customer",
  tailor: "/app/professional",
  designer: "/app/professional",
  vendor: "/app/vendor",
  delivery_partner: "/app/delivery",
  admin: "/app/admin",
};
