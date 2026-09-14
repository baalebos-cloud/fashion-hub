import { useState } from "react";
import { RatingInput } from "./RatingInput";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { validateReview } from "@/lib/validation/review";
import { getDisplayErrorMessage } from "@/lib/utils/errors";

export interface ReviewFormProps {
  onSubmit: (score: number, comment: string) => Promise<void>;
}

export function ReviewForm({ onSubmit }: ReviewFormProps) {
  const [score, setScore] = useState(5);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  async function handleSubmit() {
    const errors = validateReview({ score, comment });
    if (errors.length > 0) {
      setError(errors[0].message);
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(score, comment);
      setIsSubmitted(true);
    } catch (err) {
      setError(getDisplayErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isSubmitted) {
    return <p className="text-sm text-ink-soft">Thanks for your review!</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <RatingInput value={score} onChange={setScore} />
      <Textarea placeholder="How was your experience? (optional)" value={comment} onChange={(e) => setComment(e.target.value)} rows={3} />
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button onClick={handleSubmit} isLoading={isSubmitting} className="self-start">Submit review</Button>
    </div>
  );
}
