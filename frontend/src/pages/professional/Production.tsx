import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { professionalRoutes } from "@/config/routes.config";

export default function Production() {
  const { orders, isLoading } = useOrders();
  if (isLoading) return <LoadingScreen />;

  const inProduction = orders.filter((o) => o.status === "in_production");

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">In production</h1>
      <OrderList orders={inProduction} detailsPathFor={professionalRoutes.orderDetails} />
    </div>
  );
}
