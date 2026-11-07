import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";

export type InteractionEventIn = {
  event_type: "view" | "search" | "booking_started";
  item_type?: "product" | "design" | "professional";
  item_id?: string;
  search_query?: string;
  source?: string;
};

export type InteractionBatch = { anonymous_id?: string; events: InteractionEventIn[] };

export const interactionsApi = {
  async send(batch: InteractionBatch): Promise<number> {
    const result = await apiClient.post<{ accepted: number }>(endpoints.interactions.events, batch);
    return result.data.accepted;
  },
  async getPreference(): Promise<boolean> {
    const result = await apiClient.get<{ personalization_enabled: boolean }>(endpoints.interactions.preference);
    return result.data.personalization_enabled;
  },
  async setPreference(enabled: boolean): Promise<boolean> {
    const result = await apiClient.put<{ personalization_enabled: boolean }>(
      endpoints.interactions.preference, { personalization_enabled: enabled });
    return result.data.personalization_enabled;
  },
};
