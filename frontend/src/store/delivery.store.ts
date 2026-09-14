import { create } from "zustand";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery } from "@/types/delivery";

interface DeliveryState {
  current: Delivery | null;
  isLoading: boolean;
  fetchById: (id: string) => Promise<void>;
}

export const useDeliveryStore = create<DeliveryState>((set) => ({
  current: null,
  isLoading: false,
  fetchById: async (id) => {
    set({ isLoading: true });
    try {
      const current = await deliveriesApi.getById(id);
      set({ current });
    } finally {
      set({ isLoading: false });
    }
  },
}));
