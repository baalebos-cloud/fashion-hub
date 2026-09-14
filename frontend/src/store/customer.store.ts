import { create } from "zustand";
import type { Customer } from "@/types/customer";
import { customersApi } from "@/api/customers.api";

interface CustomerState {
  customer: Customer | null;
  isLoading: boolean;
  fetch: () => Promise<void>;
}

export const useCustomerStore = create<CustomerState>((set) => ({
  customer: null,
  isLoading: false,
  fetch: async () => {
    set({ isLoading: true });
    try {
      const customer = await customersApi.getMe();
      set({ customer });
    } finally {
      set({ isLoading: false });
    }
  },
}));
