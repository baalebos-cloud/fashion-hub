import { create } from "zustand";
import type { Professional } from "@/types/professional";
import { professionalsApi } from "@/api/professionals.api";

interface ProfessionalState {
  current: Professional | null;
  isLoading: boolean;
  fetchById: (id: string) => Promise<void>;
}

export const useProfessionalStore = create<ProfessionalState>((set) => ({
  current: null,
  isLoading: false,
  fetchById: async (id) => {
    set({ isLoading: true });
    try {
      const current = await professionalsApi.getById(id);
      set({ current });
    } finally {
      set({ isLoading: false });
    }
  },
}));
