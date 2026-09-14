import { useOrders } from "@/hooks/use-orders";
import { Table, type Column } from "@/components/ui/table";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { LoadingScreen } from "@/components/common/LoadingScreen";
import { formatCurrency } from "@/lib/formatters/currency";
import type { Order, CustomerOrderStatus } from "@/types/order";

export default function Orders() {
  const { orders, isLoading } = useOrders();
  if (isLoading) return <LoadingScreen />;

  const columns: Column<Order>[] = [
    { header: "Order", render: (o) => o.order_number },
    { header: "Type", render: (o) => o.order_type.replace("_", " ") },
    { header: "Total", render: (o) => formatCurrency(o.total_amount, o.currency) },
    { header: "Status", render: (o) => <OrderStatusBadge status={o.status as CustomerOrderStatus} /> },
  ];

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">All orders</h1>
      <Table columns={columns} rows={orders} />
    </div>
  );
}
