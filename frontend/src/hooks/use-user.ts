import { useUserStore } from "@/store/user.store";
import { useAuth } from "./use-auth";

export function useUser() {
  const { user } = useAuth();
  const { isSaving, error, updateProfile } = useUserStore();
  return { user, isSaving, error, updateProfile };
}
