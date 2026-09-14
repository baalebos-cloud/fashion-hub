import { create } from "zustand";
import { getLocalItem, setLocalItem } from "@/lib/storage/local-storage";

interface UIState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  activeModal: string | null;
  openModal: (id: string) => void;
  closeModal: () => void;
}

/** Purely cosmetic app-shell state — never business data. Sidebar
 * collapse preference persists across sessions via localStorage since
 * it's a harmless UI preference, unlike auth tokens (see lib/auth/token.ts
 * for why those use sessionStorage instead). */
export const useUIStore = create<UIState>((set, get) => ({
  isSidebarCollapsed: getLocalItem("fashionhub.sidebar_collapsed", false),
  toggleSidebar: () => {
    const next = !get().isSidebarCollapsed;
    setLocalItem("fashionhub.sidebar_collapsed", next);
    set({ isSidebarCollapsed: next });
  },
  activeModal: null,
  openModal: (id) => set({ activeModal: id }),
  closeModal: () => set({ activeModal: null }),
}));
