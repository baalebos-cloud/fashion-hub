import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { measurementsApi } from "@/api/measurements.api";
import { measurementKeys } from "@/api/query-keys";
import { useAuth } from "@/hooks/use-auth";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { MeasurementField, MeasurementProfile } from "@/types/measurement";

export function useMeasurements() {
  const { user } = useAuth();
  const userId = user?.id ?? "anonymous";
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: measurementKeys.user(userId),
    queryFn: measurementsApi.list,
    enabled: Boolean(user?.id),
    staleTime: 1000 * 60 * 5,
  });
  const create = useMutation({
    mutationFn: ({ label, garmentType, fields }: {
      label: string; garmentType: string | undefined; fields: MeasurementField[]
    }) => measurementsApi.create(label, garmentType, fields),
    onSuccess: async (created: MeasurementProfile) => {
      queryClient.setQueryData<MeasurementProfile[]>(
        measurementKeys.user(userId),
        (old) => old ? [...old.filter((item) => item.id !== created.id), created] : [created],
      );
      await queryClient.invalidateQueries({ queryKey: measurementKeys.user(userId) });
    },
  });

  async function createProfile(label: string, garmentType: string | undefined, fields: MeasurementField[]) {
    return create.mutateAsync({ label, garmentType, fields });
  }

  return {
    profiles: query.data ?? [],
    error: query.error ? getDisplayErrorMessage(query.error) : null,
    isLoading: query.isLoading,
    isSaving: create.isPending,
    createProfile,
    refetch: async () => { await query.refetch(); },
  };
}
