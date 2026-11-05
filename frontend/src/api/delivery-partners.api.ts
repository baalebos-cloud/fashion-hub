import { apiClient } from "@/lib/api/client";
import type { Delivery } from "@/types/delivery";

export type VehicleType = "bike" | "car" | "van" | "foot";

export interface RiderProfile {
  id: string;
  user_id: string;
  vehicle_type: VehicleType | null;
  is_verified: boolean;
  is_available: boolean;
  average_rating: number;
}

export const deliveryPartnersApi = {
  async me(): Promise<RiderProfile> {
    return (await apiClient.get<RiderProfile>("/delivery-partners/me")).data;
  },
  async setAvailability(isAvailable: boolean): Promise<RiderProfile> {
    return (await apiClient.put<RiderProfile>("/delivery-partners/me/availability", { is_available: isAvailable })).data;
  },
  /** Changing vehicle sends the rider back for re-verification (server rule). */
  async saveVehicle(vehicleType: VehicleType): Promise<RiderProfile> {
    return (await apiClient.put<RiderProfile>("/delivery-partners/me", { vehicle_type: vehicleType })).data;
  },
  async activeDeliveries(): Promise<Delivery[]> {
    return (await apiClient.get<Delivery[]>("/deliveries/mine/active")).data;
  },
};
