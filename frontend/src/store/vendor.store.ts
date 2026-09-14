import { create } from "zustand";
import type { Vendor } from "@/types/vendor";
import { vendorsApi } from "@/api/vendors.api";

interface VendorState {
  current: Vendor | null;
  isLoading: boolean;
  fetchById: (id: string) => Promise<void>;
}

export const useVendorStore = create<VendorState>((set) => ({
  current: null,
  isLoading: false,
  fetchById: async (id) => {
    set({ isLoading: true });
    try {
      const current = await vendorsApi.getById(id);
      set({ current });
    } finally {
      set({ isLoading: false });
    }
  },
}));
