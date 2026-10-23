import { useEffect, useState } from "react";
import { ReviewList } from "@/components/reviews/ReviewList";
import { reviewsApi } from "@/api/reviews.api";
import type { Review } from "@/types/review";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export default function Reviews() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    reviewsApi.mine().then((items) => {
      if (active) setReviews(items);
    }).catch((err: unknown) => {
      if (active) setError(getDisplayErrorMessage(err));
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Your reviews</h1>
      {loading && <p role="status">Loading reviews…</p>}
      {error && <p role="alert" className="text-thread">{error}</p>}
      {!loading && !error && <ReviewList reviews={reviews} />}
    </div>
  );
}
