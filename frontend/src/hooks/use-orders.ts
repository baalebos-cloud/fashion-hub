import { useEffect } from "react";
import { useOrderStore } from "@/store/order.store";

/** List-view hook (Orders.tsx pages across every role). Fetches once on
 * mount; call `refetch` after an action elsewhere invalidates the list. */
export function useOrders() {
  const { orders, isLoading, error, fetchList } = useOrderStore();

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  return { orders, isLoading, error, refetch: fetchList };
}
