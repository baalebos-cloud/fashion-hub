import { useCallback, useEffect, useState } from "react";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { measurementsApi } from "@/api/measurements.api";
import type { MeasurementField, MeasurementProfile } from "@/types/measurement";

export function useMeasurements() {
  const [profiles, setProfiles] = useState<MeasurementProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const refetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setProfiles(await measurementsApi.list());
    } catch (err) {
      setError(getDisplayErrorMessage(err));
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

  return { profiles, error, isLoading, createProfile, refetch };
}
