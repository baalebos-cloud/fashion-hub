import { apiClient } from "@/lib/api/client";
import type { Storefront, StorefrontLink } from "@/types/storefront";

export const storefrontsApi = {
  async getPublic(handle: string): Promise<Storefront> {
    return (await apiClient.get<Storefront>(`/storefronts/${encodeURIComponent(handle)}`)).data;
  },
  async myLink(): Promise<StorefrontLink> {
    return (await apiClient.get<StorefrontLink>("/storefronts/me")).data;
  },
  async changeHandle(handle: string): Promise<StorefrontLink> {
    return (await apiClient.put<StorefrontLink>("/storefronts/me", { handle })).data;
  },
};

/** Pre-filled WhatsApp share text; wa.me opens the app's share sheet on phones. */
export function whatsappShareUrl(displayName: string | null | undefined, shareUrl: string): string {
  const text = displayName ? `Shop with ${displayName} on Tailora: ${shareUrl}` : `Shop with me on Tailora: ${shareUrl}`;
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

/** Same rules as the backend: 3-30 chars, lowercase letters, digits, single hyphens. */
export const HANDLE_PATTERN = /^[a-z0-9](?:[a-z0-9]|-(?!-)){1,28}[a-z0-9]$/;
