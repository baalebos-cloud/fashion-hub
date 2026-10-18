import { useEffect, useState } from "react";
import { ordersApi } from "@/api/orders.api";
import { OrderList } from "@/components/orders/OrderList";
import { Button } from "@/components/ui/button";
import { professionalRoutes } from "@/config/routes.config";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Order } from "@/types/order";

export default function VendorOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    ordersApi.list({ perspective: "buying", order_type: "vendor_order", page }).then((values) => { if (active) setOrders(values); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page]);
  return <div className="flex flex-col gap-5">
    <h1 className="font-display text-xl text-ink">Material orders</h1>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Loading orders…</p> : <OrderList orders={orders} detailsPathFor={professionalRoutes.vendorOrderDetails} />}
    <div className="flex gap-4"><Button disabled={loading || page === 1} onClick={() => setPage((value) => value - 1)}>Previous</Button><span>Page {page}</span><Button disabled={loading || orders.length < 20} onClick={() => setPage((value) => value + 1)}>Next</Button></div>
  </div>;
}
