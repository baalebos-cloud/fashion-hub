import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { professionalRoutes } from "@/config/routes.config";

/** This professional's orders as the BUYER of vendor materials
 * (order_type=vendor_order) — distinct from Orders.tsx, which shows
 * customer orders where this professional is the SELLER. */
export default function VendorOrders() {
  const { orders, isLoading } = useOrders();
  const vendorOrders = orders.filter((o) => o.order_type === "vendor_order");

  if (isLoading) return <LoadingScreen />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Vendor orders</h1>
      <OrderList orders={vendorOrders} detailsPathFor={professionalRoutes.vendorOrderDetails} />
    </div>
  );
}
