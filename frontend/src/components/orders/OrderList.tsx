import { OrderCard } from "./OrderCard";
import { EmptyState } from "@/components/ui/empty-state";
import type { Order } from "@/types/order";

export function OrderList({ orders, detailsPathFor }: { orders: Order[]; detailsPathFor: (id: string) => string }) {
  if (orders.length === 0) {
    return <EmptyState title="No orders yet" description="Orders you place or receive will show up here." />;
  }

  return (
    <div className="flex flex-col gap-3">
      {orders.map((order) => (
        <OrderCard key={order.id} order={order} detailsPath={detailsPathFor(order.id)} />
      ))}
    </div>
  );
}
