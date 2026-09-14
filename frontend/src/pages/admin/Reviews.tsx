import { useState } from "react";
import { ReviewList } from "@/components/reviews/ReviewList";
import type { Review } from "@/types/review";

/** Requires `GET /admin/reviews?flagged=true`. See Users.tsx. */
export default function Reviews() {
  const [reviews] = useState<Review[]>([]);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Reviews</h1>
      <ReviewList reviews={reviews} />
    </div>
  );
}
