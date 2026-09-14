import { create } from "zustand";
import { usersApi } from "@/api/users.api";
import type { User } from "@/types/user";

/**
 * Editable profile state, separate from auth.store.ts's `user` (which is
 * the authentication identity). Most components should read the current
 * user via hooks/use-auth.ts; this store exists for the profile-editing
 * flow specifically (ProfileForm), so a half-edited draft doesn't leak
 * into the auth-derived user object used for role checks elsewhere.
 */
interface UserState {
  isSaving: boolean;
  error: string | null;
  updateProfile: (payload: Partial<Pick<User, "full_name" | "timezone">>) => Promise<User>;
}

export const useUserStore = create<UserState>((set) => ({
  isSaving: false,
  error: null,
  updateProfile: async (payload) => {
    set({ isSaving: true, error: null });
    try {
      const updated = await usersApi.updateProfile(payload);
      return updated;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Could not save profile." });
      throw err;
    } finally {
      set({ isSaving: false });
    }
  },
}));
