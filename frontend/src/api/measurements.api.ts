import { apiClient } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { MeasurementField, MeasurementProfile } from "@/types/measurement";

export const measurementsApi = {
  async list(): Promise<MeasurementProfile[]> {
    const response = await apiClient.get<MeasurementProfile[]>(endpoints.measurements.list);
    return response.data;
  },

  async create(label: string, garmentType: string | undefined, fields: MeasurementField[]): Promise<MeasurementProfile> {
    const response = await apiClient.post<MeasurementProfile>(endpoints.measurements.create, {
      label,
      garment_type: garmentType,
      fields,
    });
    return response.data;
  },
};
