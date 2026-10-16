import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { AddressInput, SavedAddress } from "@/types/address";

export const addressesApi = {
  async list(): Promise<SavedAddress[]> {
    return (await apiClient.get<SavedAddress[]>(endpoints.addresses.list)).data;
  },
  async create(payload: AddressInput): Promise<SavedAddress> {
    return (await apiClient.post<SavedAddress>(endpoints.addresses.list, payload)).data;
  },
};
