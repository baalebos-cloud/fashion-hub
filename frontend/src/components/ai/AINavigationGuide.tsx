import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import {
  customerRoutes,
  professionalRoutes,
  vendorRoutes,
  deliveryRoutes,
  adminRoutes,
} from "@/config/routes.config";
import type { UserRole } from "@/types/auth";

/**
 * IMPORTANT — the boundary this component exists to enforce:
 *
 * Seam is only ever allowed to tell a person where to go and how a
 * feature works. It must never bypass frontend route guards or backend
 * authorization — see backend/app/integrations/ai/prompts.py's system
 * prompt, which instructs the model itself never to reveal or act on
 * another user's data.
 *
 * Concretely, that means this component:
 *   - Only renders a link if the destination is in the CURRENT user's own
 *     role-scoped route map below — never an arbitrary path the model
 *     might mention in free text.
 *   - Renders a plain <Link>, which still passes through AuthGuard/RoleGuard
 *     exactly like any other in-app navigation. There is no special
 *     "AI-granted" navigation path that skips those checks.
 *   - Never constructs a link to another user's resource (an order ID,
 *     a conversation ID) from assistant text; only to static, role-level
 *     destinations (a page, not a record).
 */
const NAMED_DESTINATIONS: Record<UserRole, Record<string, string>> = {
  customer: {
    orders: customerRoutes.orders,
    "find a tailor": customerRoutes.findProfessionals,
    "find a designer": customerRoutes.findProfessionals,
    measurements: customerRoutes.measurements,
    invoices: customerRoutes.invoices,
    cart: customerRoutes.cart,
    favorites: customerRoutes.favorites,
    messages: customerRoutes.messages,
  },
  tailor: {
    orders: professionalRoutes.orders,
    "vendor marketplace": professionalRoutes.vendorMarketplace,
    cart: professionalRoutes.cart,
    portfolio: professionalRoutes.portfolio,
    verification: professionalRoutes.verification,
  },
  designer: {
    orders: professionalRoutes.orders,
    portfolio: professionalRoutes.portfolio,
    verification: professionalRoutes.verification,
  },
  vendor: {
    products: vendorRoutes.products,
    orders: vendorRoutes.orders,
    inventory: vendorRoutes.inventory,
  },
  delivery_partner: {
    "delivery requests": deliveryRoutes.requests,
    "active deliveries": deliveryRoutes.active,
  },
  admin: {
    kyc: adminRoutes.kyc,
    kyb: adminRoutes.kyb,
    "audit logs": adminRoutes.auditLogs,
  },
};

export interface AINavigationGuideProps {
  /** A short destination key the assistant's structured response
   * identified (e.g. from AIAction.payload.navigate_to on the backend) —
   * NOT raw free-text parsed client-side, which would defeat the purpose
   * of this allow-list. */
  destinationKey?: string;
}

export function AINavigationGuide({ destinationKey }: AINavigationGuideProps) {
  const { user } = useAuth();
  if (!user || !destinationKey) return null;

  const path = NAMED_DESTINATIONS[user.role]?.[destinationKey.toLowerCase()];
  if (!path) return null;

  return (
    <Link
      to={path}
      className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-line bg-paper px-3 py-1.5 text-xs font-medium text-brass-deep hover:border-brass"
    >
      Take me there →
    </Link>
  );
}
