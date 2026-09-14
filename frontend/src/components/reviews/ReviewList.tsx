import { ReviewCard } from "./ReviewCard";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils/cn";
import type { Review } from "@/types/review";

export function ReviewList({ reviews, className }: { reviews: Review[]; className?: string }) {
  if (reviews.length === 0) {
    return <EmptyState title="No reviews yet" />;
  }

  return (
    <div className={cn(className)}>
      {reviews.map((review) => (
        <ReviewCard key={review.id} review={review} />
      ))}
    </div>
  );
}
