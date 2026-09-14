import { useEffect, useState } from "react";
import { designsApi } from "@/api/designs.api";
import type { Design } from "@/types/design";

export function useDesigns(professionalId?: string) {
  const [designs, setDesigns] = useState<Design[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    designsApi
      .list({ professionalId })
      .then((response) => setDesigns(response.items))
      .finally(() => setIsLoading(false));
  }, [professionalId]);

  return { designs, isLoading };
}
