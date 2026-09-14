import { create } from "zustand";
import { ordersApi } from "@/api/orders.api";
import type { Order, OrderTimelineEntry } from "@/types/order";

interface OrderState {
  orders: Order[];
  currentOrder: Order | null;
  timeline: OrderTimelineEntry[];
  isLoading: boolean;
  error: string | null;

  fetchList: () => Promise<void>;
  fetchById: (id: string) => Promise<void>;
  fetchTimeline: (id: string) => Promise<void>;
  /** Every transition below just calls the backend and replaces
   * currentOrder with its response — the backend's returned status is
   * always what's rendered, never a locally-guessed next status. */
  accept: (id: string) => Promise<void>;
  startProduction: (id: string) => Promise<void>;
  markReady: (id: string) => Promise<void>;
  ship: (id: string) => Promise<void>;
  markReceived: (id: string) => Promise<void>;
  cancel: (id: string, note?: string) => Promise<void>;
}

export const useOrderStore = create<OrderState>((set) => ({
  orders: [],
  currentOrder: null,
  timeline: [],
  isLoading: false,
  error: null,

  fetchList: async () => {
    set({ isLoading: true, error: null });
    try {
      const orders = await ordersApi.list();
      set({ orders });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not load orders." });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchById: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const currentOrder = await ordersApi.getById(id);
      set({ currentOrder });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not load this order." });
    } finally {
      set({ isLoading: false });
    }
  },

  fetchTimeline: async (id) => {
    const timeline = await ordersApi.getTimeline(id);
    set({ timeline });
  },

  accept: async (id) => set({ currentOrder: await ordersApi.accept(id) }),
  startProduction: async (id) => set({ currentOrder: await ordersApi.startProduction(id) }),
  markReady: async (id) => set({ currentOrder: await ordersApi.markReady(id) }),
  ship: async (id) => set({ currentOrder: await ordersApi.ship(id) }),
  markReceived: async (id) => set({ currentOrder: await ordersApi.markReceived(id) }),
  cancel: async (id, note) => set({ currentOrder: await ordersApi.cancel(id, note) }),
}));
