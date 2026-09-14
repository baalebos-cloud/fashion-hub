import { useEffect } from "react";
import { useCartStore } from "@/store/cart.store";

export function useCart() {
  const { summary, isLoading, error, fetchSummary, addItem, updateItem, removeItem } = useCartStore();

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return { summary, isLoading, error, addItem, updateItem, removeItem, refetch: fetchSummary };
}
