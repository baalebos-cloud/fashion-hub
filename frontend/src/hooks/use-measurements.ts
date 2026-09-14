import { useCallback, useEffect, useState } from "react";
import { measurementsApi } from "@/api/measurements.api";
import type { MeasurementField, MeasurementProfile } from "@/types/measurement";

export function useMeasurements() {
  const [profiles, setProfiles] = useState<MeasurementProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    try {
      setProfiles(await measurementsApi.list());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  async function createProfile(label: string, garmentType: string | undefined, fields: MeasurementField[]) {
    const created = await measurementsApi.create(label, garmentType, fields);
    setProfiles((prev) => [...prev, created]);
    return created;
  }

  return { profiles, isLoading, createProfile, refetch };
}
