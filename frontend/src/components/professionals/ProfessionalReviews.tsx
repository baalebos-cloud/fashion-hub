import { useReviews } from "@/hooks/use-reviews";
import { ReviewList } from "@/components/reviews/ReviewList";
import { ReviewSummary } from "@/components/reviews/ReviewSummary";

export function ProfessionalReviews({ professionalId, averageRating, reviewCount }: { professionalId: string; averageRating: number; reviewCount: number }) {
  const { reviews, isLoading } = useReviews(professionalId);

  return (
    <div>
      <h2 className="mb-3 text-sm font-medium text-ink-soft">Reviews</h2>
      <ReviewSummary average={averageRating} count={reviewCount} />
      {!isLoading && <ReviewList reviews={reviews} className="mt-4" />}
    </div>
  );
}
