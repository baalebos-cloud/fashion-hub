import { ReviewList } from "@/components/reviews/ReviewList";

/** Requires a "my reviews" endpoint (e.g. GET /reviews?reviewer_id=me) —
 * the current backend scaffold only exposes GET /reviews?professional_id=
 * (see backend/app/api/v1/reviews.py stub and api/reviews.api.ts). Once
 * that lands, fetch and pass real reviews here instead of an empty list. */
export default function Reviews() {
  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Your reviews</h1>
      <ReviewList reviews={[]} />
    </div>
  );
}
