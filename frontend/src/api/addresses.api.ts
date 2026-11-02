import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { AddressInput, SavedAddress } from "@/types/address";

export const addressesApi = {
  async list(): Promise<SavedAddress[]> {
    return (await apiClient.get<SavedAddress[]>(endpoints.addresses.list)).data;
  },
  async update(id: string, payload: AddressInput): Promise<SavedAddress> {
    return (await apiClient.put<SavedAddress>(`${endpoints.addresses.list}/${id}`, payload)).data;
  },
  async setDefault(id: string): Promise<SavedAddress> {
    return (await apiClient.put<SavedAddress>(`${endpoints.addresses.list}/${id}/default`)).data;
  },
  async remove(id: string): Promise<void> {
    await apiClient.delete(`${endpoints.addresses.list}/${id}`);
  },
  async create(payload: AddressInput): Promise<SavedAddress> {
    return (await apiClient.post<SavedAddress>(endpoints.addresses.list, payload)).data;
  },
};
