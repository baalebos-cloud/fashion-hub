import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { vendorRoutes } from "@/config/routes.config";

export default function Orders() {
  const { orders, isLoading } = useOrders();
  if (isLoading) return <LoadingScreen />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Orders</h1>
      <OrderList orders={orders} detailsPathFor={vendorRoutes.orderDetails} />
    </div>
  );
}
