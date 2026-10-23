import { create } from "zustand";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery } from "@/types/delivery";

interface DeliveryState {
  current: Delivery | null;
  isLoading: boolean;
  error: string | null;
  fetchById: (id: string) => Promise<void>;
}

export const useDeliveryStore = create<DeliveryState>((set) => ({
  current: null,
  isLoading: false,
  error: null,
  fetchById: async (id) => {
    set({ isLoading: true, error: null, current: null });
    try {
      const current = await deliveriesApi.getById(id);
      set({ current });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not load delivery." });
    } finally {
      set({ isLoading: false });
    }
  },
}));
