import { create } from "zustand";
import { cartApi } from "@/api/cart.api";
import type { CartSummary } from "@/types/cart";

interface CartState {
  summary: CartSummary | null;
  isLoading: boolean;
  error: string | null;

  fetchSummary: () => Promise<void>;
  addItem: (productVariantId: string, quantity: number) => Promise<void>;
  updateItem: (cartItemId: string, quantity: number) => Promise<void>;
  removeItem: (cartItemId: string) => Promise<void>;
}

/**
 * Deliberately NOT optimistic: every mutation re-fetches (or uses the
 * response of) the authoritative cart from the backend rather than
 * guessing the new state locally. This matters because the backend can
 * reject a quantity change the moment a vendor's stock changes underneath
 * the person — see backend/docs/cart.md's "vendor sells out" edge case.
 * An optimistic UI here would show a false success right before the real
 * checkout-time check fails.
 */
export const useCartStore = create<CartState>((set, get) => ({
  summary: null,
  isLoading: false,
  error: null,

  fetchSummary: async () => {
    set({ isLoading: true, error: null });
    try {
      const summary = await cartApi.getSummary();
      set({ summary });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not load your cart." });
    } finally {
      set({ isLoading: false });
    }
  },

  addItem: async (productVariantId, quantity) => {
    set({ error: null });
    try {
      const summary = await cartApi.addItem(productVariantId, quantity);
      set({ summary });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not add this item." });
      throw err;
    }
  },

  updateItem: async (cartItemId, quantity) => {
    set({ error: null });
    try {
      const summary = await cartApi.updateItem(cartItemId, quantity);
      set({ summary });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not update quantity." });
      throw err;
    }
  },

  removeItem: async (cartItemId) => {
    await cartApi.removeItem(cartItemId);
    await get().fetchSummary();
  },
}));
