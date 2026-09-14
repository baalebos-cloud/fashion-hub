import { useParams } from "react-router-dom";
import { useOrders } from "@/hooks/use-orders";
import { OrderList } from "@/components/orders/OrderList";
import { professionalRoutes } from "@/config/routes.config";

export default function CustomerDetails() {
  const { customerId } = useParams<{ customerId: string }>();
  const { orders } = useOrders();
  const customerOrders = orders.filter((o) => o.buyer_user_id === customerId || o.id === customerId);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Order history</h1>
      <OrderList orders={customerOrders} detailsPathFor={professionalRoutes.orderDetails} />
    </div>
  );
}
