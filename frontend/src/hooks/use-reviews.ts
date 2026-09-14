import { useEffect, useState } from "react";
import { reviewsApi } from "@/api/reviews.api";
import type { Review } from "@/types/review";

export function useReviews(professionalId: string | undefined) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!professionalId) return;
    setIsLoading(true);
    reviewsApi
      .listForProfessional(professionalId)
      .then(setReviews)
      .finally(() => setIsLoading(false));
  }, [professionalId]);

  return { reviews, isLoading };
}
