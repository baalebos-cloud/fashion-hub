import { useAuth } from "@/hooks/use-auth";
import { useReviews } from "@/hooks/use-reviews";
import { ReviewList } from "@/components/reviews/ReviewList";
import { ReviewSummary } from "@/components/reviews/ReviewSummary";

export default function Reviews() {
  const { user } = useAuth();
  const { reviews, isLoading } = useReviews(user?.id);

  return (
    <div>
      <h1 className="mb-6 font-display text-xl text-ink">Reviews</h1>
      <ReviewSummary average={reviews.length ? reviews.reduce((s, r) => s + (r.score ?? 0), 0) / reviews.length : 0} count={reviews.length} />
      {!isLoading && <ReviewList reviews={reviews} className="mt-4" />}
    </div>
  );
}
