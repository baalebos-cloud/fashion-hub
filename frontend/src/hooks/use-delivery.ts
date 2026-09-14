import { useEffect } from "react";
import { useDeliveryStore } from "@/store/delivery.store";

export function useDelivery(deliveryId: string | undefined) {
  const { current, isLoading, fetchById } = useDeliveryStore();

  useEffect(() => {
    if (deliveryId) fetchById(deliveryId);
  }, [deliveryId, fetchById]);

  return { delivery: current, isLoading };
}
