import { apiClient } from "@/lib/api/client";
import type { WeatherSnapshot } from "@/types/weather";

/**
 * Mirrors backend/app/api/v1/weather.py + the order-specific weather
 * endpoint in orders.py. The order-specific one is preferred whenever an
 * order exists -- it aims the forecast at the delivery's live ETA, not
 * just "right now" (see backend/docs/weather.md).
 */
export const weatherApi = {
  async getCurrent(latitude: number, longitude: number): Promise<WeatherSnapshot> {
    const response = await apiClient.get<WeatherSnapshot>("/weather/current", { params: { latitude, longitude } });
    return response.data;
  },

  async getForOrder(orderId: string): Promise<WeatherSnapshot> {
    const response = await apiClient.get<WeatherSnapshot>(`/orders/${orderId}/weather`);
    return response.data;
  },
};
