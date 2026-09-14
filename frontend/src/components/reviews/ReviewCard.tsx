import { Avatar } from "@/components/ui/avatar";
import { DateTimeDisplay } from "@/components/common/DateTimeDisplay";
import type { Review } from "@/types/review";

export function ReviewCard({ review }: { review: Review }) {
  return (
    <div className="flex gap-3 border-b border-line py-4 last:border-0">
      <Avatar name="Customer" size="sm" />
      <div>
        {review.score != null && (
          <div className="text-sm text-brass" aria-label={`${review.score} out of 5 stars`}>
            {"★".repeat(review.score)}
            <span className="text-line">{"★".repeat(5 - review.score)}</span>
          </div>
        )}
        {review.comment && <p className="mt-1 text-sm text-ink">{review.comment}</p>}
        {review.created_at && (
          <p className="mt-1 text-xs text-ink-soft">
            <DateTimeDisplay value={review.created_at} format="relative" />
          </p>
        )}
      </div>
    </div>
  );
}
