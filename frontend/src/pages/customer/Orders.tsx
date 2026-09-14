import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { customerRoutes } from "@/config/routes.config";

export default function Orders() {
  const { orders, isLoading, error } = useOrders();

  if (isLoading) return <LoadingScreen label="Loading your orders…" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Your orders</h1>
      {error && <p className="mb-4 text-sm text-thread">{error}</p>}
      <OrderList orders={orders} detailsPathFor={customerRoutes.orderDetails} />
    </div>
  );
}
