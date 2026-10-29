import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils/cn";
import {
  customerRoutes,
  professionalRoutes,
  vendorRoutes,
  deliveryRoutes,
  adminRoutes,
} from "@/config/routes.config";
import type { UserRole } from "@/types/auth";

export interface NavItem {
  label: string;
  path: string;
  icon?: React.ReactNode;
}

export interface NavGroup {
  heading?: string;
  items: NavItem[];
}

function Icon({ d }: { d: string }) {
  return (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0">
      <path d={d} fill="currentColor" />
    </svg>
  );
}

const ICONS = {
  home: "M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z",
  orders: "M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-7 3a3 3 0 1 1 0 6 3 3 0 0 1 0-6zm6 13H6v-.9c0-2 4-3.1 6-3.1s6 1.1 6 3.1V19z",
  search: "M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
  measure: "M21 6.5l-4-4-8.5 8.5-2 4.5 4.5-2L21 6.5zm-14 9l-1.5.7.7-1.5 8.3-8.3 .8.8L7 15.5zM3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z",
  design: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z",
  payment: "M20 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z",
  invoice: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15h8v2H8zm0-4h8v2H8z",
  message: "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z",
  notification: "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
  settings: "M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.02 7.02 0 0 0-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.48.48 0 0 0-.59.22L2.74 8.87a.47.47 0 0 0 .12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.47.47 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z",
  kyc: "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 4a3 3 0 1 1 0 6 3 3 0 0 1 0-6zm0 14c-2.67 0-5.01-1.33-6.43-3.36C7.12 14.26 9.43 13.5 12 13.5s4.88.76 6.43 2.14C16.99 17.67 14.67 19 12 19z",
  delivery: "M20 8h-3V4H3c-1.1 0-2 .9-2 2v11h2a3 3 0 0 0 6 0h6a3 3 0 0 0 6 0h2v-5l-3-4zm-.5 1.5 1.96 2.5H17V9.5h2.5zM6 18a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm13 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2z",
  referral: "M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z",
  portfolio: "M22 16V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2zm-11-4 2.03 2.71L16 11l4 5H8l3-4zM2 6v14a2 2 0 0 0 2 2h14v-2H4V6H2z",
  vendor: "M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96C5 16.1 6.9 18 9 18h12v-2H9.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63H19c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 23.43 5H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z",
  users: "M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z",
  audit: "M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6c0-1.1-.89-2-2-2zm0 16H5V9h14v11z",
  report: "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z",
  favorite: "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z",
  location: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 0 5.5z",
  production: "M19.8 18.4 14 10.67V6.5l1.35-1.69c.26-.33.03-.81-.39-.81H9.04c-.42 0-.65.48-.39.81L10 6.5v4.17L4.2 18.4c-.49.66-.02 1.6.8 1.6h14c.82 0 1.29-.94.8-1.6z",
  cart: "M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96C5 16.1 6.9 18 9 18h12v-2H9.42c-.14 0-.25-.11-.25-.25l.03-.12.9-1.63H19c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 23.43 5H5.21l-.94-2H1zm16 16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z",
  dispute: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
  earnings: "M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z",
};

const GROUPS_BY_ROLE: Record<UserRole, NavGroup[]> = {
  customer: [
    {
      items: [
        { label: "Overview", path: customerRoutes.dashboard, icon: <Icon d={ICONS.home} /> },
        { label: "Find Tailor", path: customerRoutes.findProfessionals, icon: <Icon d={ICONS.search} /> },
        { label: "Orders", path: customerRoutes.orders, icon: <Icon d={ICONS.orders} /> },
        { label: "Measurements", path: customerRoutes.measurements, icon: <Icon d={ICONS.measure} /> },
        { label: "Designs", path: customerRoutes.designs, icon: <Icon d={ICONS.design} /> },
        { label: "Favorites", path: customerRoutes.favorites, icon: <Icon d={ICONS.favorite} /> },
      ],
    },
    {
      heading: "Finance",
      items: [
        { label: "Invoices", path: customerRoutes.invoices, icon: <Icon d={ICONS.invoice} /> },
        { label: "Reviews", path: customerRoutes.reviews, icon: <Icon d={ICONS.report} /> },
      ],
    },
    {
      heading: "Account",
      items: [
        { label: "Messages", path: customerRoutes.messages, icon: <Icon d={ICONS.message} /> },
        { label: "Notifications", path: customerRoutes.notifications, icon: <Icon d={ICONS.notification} /> },
        { label: "Addresses", path: customerRoutes.addresses, icon: <Icon d={ICONS.location} /> },
        { label: "Settings", path: customerRoutes.settings, icon: <Icon d={ICONS.settings} /> },
      ],
    },
  ],
  tailor: [
    {
      items: [
        { label: "Overview", path: professionalRoutes.dashboard, icon: <Icon d={ICONS.home} /> },
        { label: "Customer Orders", path: professionalRoutes.orders, icon: <Icon d={ICONS.orders} /> },
        { label: "Production", path: professionalRoutes.production, icon: <Icon d={ICONS.production} /> },
        { label: "Customers", path: professionalRoutes.customers, icon: <Icon d={ICONS.users} /> },
        { label: "Measurements", path: professionalRoutes.measurements, icon: <Icon d={ICONS.measure} /> },
        { label: "Designs", path: professionalRoutes.designs, icon: <Icon d={ICONS.design} /> },
        { label: "Portfolio", path: professionalRoutes.portfolio, icon: <Icon d={ICONS.portfolio} /> },
      ],
    },
    {
      heading: "Materials",
      items: [
        { label: "Marketplace", path: professionalRoutes.vendorMarketplace, icon: <Icon d={ICONS.vendor} /> },
        { label: "Cart", path: professionalRoutes.cart, icon: <Icon d={ICONS.cart} /> },
        { label: "Material Orders", path: professionalRoutes.vendorOrders, icon: <Icon d={ICONS.delivery} /> },
      ],
    },
    {
      heading: "Finance",
      items: [
        { label: "Payments", path: professionalRoutes.payments, icon: <Icon d={ICONS.payment} /> },
        { label: "Invoices", path: professionalRoutes.invoices, icon: <Icon d={ICONS.invoice} /> },
        { label: "Referrals", path: professionalRoutes.referrals, icon: <Icon d={ICONS.referral} /> },
      ],
    },
    {
      heading: "Account",
      items: [
        { label: "KYC / KYB", path: professionalRoutes.verification, icon: <Icon d={ICONS.kyc} /> },
        { label: "Shop Location", path: professionalRoutes.location, icon: <Icon d={ICONS.location} /> },
        { label: "Messages", path: professionalRoutes.messages, icon: <Icon d={ICONS.message} /> },
        { label: "Notifications", path: professionalRoutes.notifications, icon: <Icon d={ICONS.notification} /> },
        { label: "Settings", path: professionalRoutes.settings, icon: <Icon d={ICONS.settings} /> },
      ],
    },
  ],
  designer: [],
  vendor: [
    {
      items: [
        { label: "Overview", path: vendorRoutes.dashboard, icon: <Icon d={ICONS.home} /> },
        { label: "Products", path: vendorRoutes.products, icon: <Icon d={ICONS.vendor} /> },
        { label: "Inventory", path: vendorRoutes.inventory, icon: <Icon d={ICONS.production} /> },
        { label: "Orders", path: vendorRoutes.orders, icon: <Icon d={ICONS.orders} /> },
        { label: "Delivery", path: vendorRoutes.delivery, icon: <Icon d={ICONS.delivery} /> },
      ],
    },
    {
      heading: "Finance",
      items: [
        { label: "Payments", path: vendorRoutes.payments, icon: <Icon d={ICONS.payment} /> },
        { label: "Invoices", path: vendorRoutes.invoices, icon: <Icon d={ICONS.invoice} /> },
        { label: "Referrals", path: vendorRoutes.referrals, icon: <Icon d={ICONS.referral} /> },
      ],
    },
    {
      heading: "Account",
      items: [
        { label: "KYB", path: vendorRoutes.verification, icon: <Icon d={ICONS.kyc} /> },
        { label: "Notifications", path: vendorRoutes.notifications, icon: <Icon d={ICONS.notification} /> },
        { label: "Settings", path: vendorRoutes.settings, icon: <Icon d={ICONS.settings} /> },
      ],
    },
  ],
  delivery_partner: [
    {
      items: [
        { label: "Overview", path: deliveryRoutes.dashboard, icon: <Icon d={ICONS.home} /> },
        { label: "Requests", path: deliveryRoutes.requests, icon: <Icon d={ICONS.orders} /> },
        { label: "Active Deliveries", path: deliveryRoutes.active, icon: <Icon d={ICONS.delivery} /> },
        { label: "History", path: deliveryRoutes.history, icon: <Icon d={ICONS.audit} /> },
        { label: "Earnings", path: deliveryRoutes.earnings, icon: <Icon d={ICONS.earnings} /> },
      ],
    },
    {
      heading: "Account",
      items: [
        { label: "Verification", path: deliveryRoutes.verification, icon: <Icon d={ICONS.kyc} /> },
        { label: "Notifications", path: deliveryRoutes.notifications, icon: <Icon d={ICONS.notification} /> },
        { label: "Settings", path: deliveryRoutes.settings, icon: <Icon d={ICONS.settings} /> },
      ],
    },
  ],
  admin: [
    {
      items: [
        { label: "Overview", path: adminRoutes.dashboard, icon: <Icon d={ICONS.home} /> },
        { label: "Users", path: adminRoutes.users, icon: <Icon d={ICONS.users} /> },
        { label: "Orders", path: adminRoutes.orders, icon: <Icon d={ICONS.orders} /> },
        { label: "Payments", path: adminRoutes.payments, icon: <Icon d={ICONS.payment} /> },
        { label: "Deliveries", path: adminRoutes.deliveries, icon: <Icon d={ICONS.delivery} /> },
      ],
    },
    {
      heading: "Verification",
      items: [
        { label: "KYC", path: adminRoutes.kyc, icon: <Icon d={ICONS.kyc} /> },
        { label: "KYB", path: adminRoutes.kyb, icon: <Icon d={ICONS.kyc} /> },
        { label: "Disputes", path: adminRoutes.disputes, icon: <Icon d={ICONS.dispute} /> },
      ],
    },
    {
      heading: "Reports",
      items: [
        { label: "Reports", path: adminRoutes.reports, icon: <Icon d={ICONS.report} /> },
        { label: "Audit Logs", path: adminRoutes.auditLogs, icon: <Icon d={ICONS.audit} /> },
        { label: "Notifications", path: adminRoutes.notifications, icon: <Icon d={ICONS.notification} /> },
        { label: "Settings", path: adminRoutes.settings, icon: <Icon d={ICONS.settings} /> },
      ],
    },
  ],
};
GROUPS_BY_ROLE.designer = GROUPS_BY_ROLE.tailor;

export function Sidebar({
  role,
  mobile = false,
  onNavigate,
}: {
  role: UserRole;
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const groups = GROUPS_BY_ROLE[role] ?? [];

  return (
    <nav
      className={
        mobile
          ? "flex h-full flex-col bg-paper"
          : "hidden md:flex md:w-[264px] md:shrink-0 md:flex-col border-r border-line bg-paper"
      }
      aria-label="Sidebar navigation"
    >
      <div className="flex flex-col gap-4 overflow-y-auto p-3 pb-6">
        {groups.map((group, gi) => (
          <div key={gi} className="flex flex-col gap-0.5">
            {group.heading && (
              <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-ink-soft/60">
                {group.heading}
              </p>
            )}
            {group.items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "flex min-h-10 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-muslin text-ink"
                      : "text-ink-soft hover:bg-muslin/60 hover:text-ink"
                  )
                }
              >
                {item.icon}
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}
