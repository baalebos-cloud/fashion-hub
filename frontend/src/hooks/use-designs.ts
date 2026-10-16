import { useEffect, useState } from "react";
import { designsApi } from "@/api/designs.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { Design } from "@/types/design";

export function useDesigns(professionalId?: string) {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError(null);
    setDesigns([]);
    designsApi.list({ professionalId })
      .then((data) => { if (active) setDesigns(data); })
      .catch((err) => { if (active) setError(getDisplayErrorMessage(err)); })
      .finally(() => { if (active) setIsLoading(false); });
    return () => { active = false; };
  }, [professionalId]);
  return { designs, isLoading, error };
}
