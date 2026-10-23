import { useEffect } from "react";
import { useDeliveryStore } from "@/store/delivery.store";

export function useDelivery(deliveryId: string | undefined) {
  const { current, isLoading, error, fetchById } = useDeliveryStore();

  useEffect(() => {
    if (deliveryId) fetchById(deliveryId);
  }, [deliveryId, fetchById]);

  return { delivery: current?.id === deliveryId ? current : null, isLoading, error };
}
