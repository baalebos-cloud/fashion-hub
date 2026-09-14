import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils/cn";
import { customerRoutes, professionalRoutes, vendorRoutes, deliveryRoutes, adminRoutes } from "@/config/routes.config";
import type { UserRole } from "@/types/auth";

interface NavItem {
  label: string;
  path: string;
}

/**
 * One nav list per role, matching the dashboards specified in the project
 * brief exactly (Customer / Professional / Vendor / Delivery / Admin).
 * `AppLayout` picks the right list based on the signed-in user's role, so
 * a tailor never sees "Add Product" and a customer never sees "KYB".
 */
const NAV_BY_ROLE: Record<UserRole, NavItem[]> = {
  customer: [
    { label: "Overview", path: customerRoutes.dashboard },
    { label: "Find Tailor", path: customerRoutes.findProfessionals },
    { label: "Find Designer", path: customerRoutes.findProfessionals },
    { label: "Orders", path: customerRoutes.orders },
    { label: "Measurements", path: customerRoutes.measurements },
    { label: "Designs", path: customerRoutes.designs },
    { label: "Favorites", path: customerRoutes.favorites },
    { label: "Invoices", path: customerRoutes.invoices },
    { label: "Reviews", path: customerRoutes.reviews },
    { label: "Messages", path: customerRoutes.messages },
    { label: "Notifications", path: customerRoutes.notifications },
    { label: "Addresses", path: customerRoutes.addresses },
    { label: "Settings", path: customerRoutes.settings },
  ],
  tailor: [
    { label: "Overview", path: professionalRoutes.dashboard },
    { label: "Customer Orders", path: professionalRoutes.orders },
    { label: "Production", path: professionalRoutes.production },
    { label: "Customers", path: professionalRoutes.customers },
    { label: "Measurements", path: professionalRoutes.measurements },
    { label: "Designs", path: professionalRoutes.designs },
    { label: "Portfolio", path: professionalRoutes.portfolio },
    { label: "Services", path: professionalRoutes.services },
    { label: "Vendor Marketplace", path: professionalRoutes.vendorMarketplace },
    { label: "Cart", path: professionalRoutes.cart },
    { label: "Vendor Orders", path: professionalRoutes.vendorOrders },
    { label: "Delivery", path: professionalRoutes.delivery },
    { label: "Payments", path: professionalRoutes.payments },
    { label: "Invoices", path: professionalRoutes.invoices },
    { label: "Reviews", path: professionalRoutes.reviews },
    { label: "KYC/KYB", path: professionalRoutes.verification },
    { label: "Shop Location", path: professionalRoutes.location },
    { label: "Messages", path: professionalRoutes.messages },
    { label: "Notifications", path: professionalRoutes.notifications },
    { label: "Settings", path: professionalRoutes.settings },
  ],
  designer: [], // same shape as tailor — populated below to avoid duplication
  vendor: [
    { label: "Overview", path: vendorRoutes.dashboard },
    { label: "Products", path: vendorRoutes.products },
    { label: "Add Product", path: vendorRoutes.addProduct },
    { label: "Categories", path: vendorRoutes.categories },
    { label: "Inventory", path: vendorRoutes.inventory },
    { label: "Orders", path: vendorRoutes.orders },
    { label: "Delivery", path: vendorRoutes.delivery },
    { label: "Payments", path: vendorRoutes.payments },
    { label: "Invoices", path: vendorRoutes.invoices },
    { label: "KYB", path: vendorRoutes.verification },
    { label: "Profile", path: vendorRoutes.profile },
    { label: "Notifications", path: vendorRoutes.notifications },
    { label: "Settings", path: vendorRoutes.settings },
  ],
  delivery_partner: [
    { label: "Overview", path: deliveryRoutes.dashboard },
    { label: "Delivery Requests", path: deliveryRoutes.requests },
    { label: "Active Deliveries", path: deliveryRoutes.active },
    { label: "Delivery History", path: deliveryRoutes.history },
    { label: "Earnings", path: deliveryRoutes.earnings },
    { label: "Verification", path: deliveryRoutes.verification },
    { label: "Profile", path: deliveryRoutes.profile },
    { label: "Notifications", path: deliveryRoutes.notifications },
    { label: "Settings", path: deliveryRoutes.settings },
  ],
  admin: [
    { label: "Overview", path: adminRoutes.dashboard },
    { label: "Users", path: adminRoutes.users },
    { label: "Customers", path: adminRoutes.customers },
    { label: "Professionals", path: adminRoutes.professionals },
    { label: "Vendors", path: adminRoutes.vendors },
    { label: "Delivery Partners", path: adminRoutes.deliveryPartners },
    { label: "Orders", path: adminRoutes.orders },
    { label: "Payments", path: adminRoutes.payments },
    { label: "Invoices", path: adminRoutes.invoices },
    { label: "Deliveries", path: adminRoutes.deliveries },
    { label: "KYC", path: adminRoutes.kyc },
    { label: "KYB", path: adminRoutes.kyb },
    { label: "Reviews", path: adminRoutes.reviews },
    { label: "Disputes", path: adminRoutes.disputes },
    { label: "Reports", path: adminRoutes.reports },
    { label: "Audit Logs", path: adminRoutes.auditLogs },
    { label: "Notifications", path: adminRoutes.notifications },
    { label: "Settings", path: adminRoutes.settings },
  ],
};
NAV_BY_ROLE.designer = NAV_BY_ROLE.tailor;

export function Sidebar({ role }: { role: UserRole }) {
  const items = NAV_BY_ROLE[role] ?? [];

  return (
    <nav className="app-sidebar hidden lg:flex lg:w-[264px] lg:flex-shrink-0 lg:flex-col border-r border-line bg-paper">
      <div className="flex flex-col gap-0.5 overflow-y-auto p-3">
        {items.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            end
            className={({ isActive }) =>
              cn(
                "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive ? "bg-muslin text-ink" : "text-ink-soft hover:bg-muslin/60 hover:text-ink"
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
