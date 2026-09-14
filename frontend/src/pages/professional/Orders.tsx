import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { professionalRoutes } from "@/config/routes.config";

export default function Orders() {
  const { orders, isLoading } = useOrders();
  if (isLoading) return <LoadingScreen label="Loading orders…" />;

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Customer orders</h1>
      <OrderList orders={orders} detailsPathFor={professionalRoutes.orderDetails} />
    </div>
  );
}
