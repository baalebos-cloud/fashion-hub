import type { FieldError } from "./auth";

export function validateReview(values: { score: number; comment?: string }): FieldError[] {
  const errors: FieldError[] = [];
  if (values.score < 1 || values.score > 5) {
    errors.push({ field: "score", message: "Rating must be between 1 and 5." });
  }
  if (values.comment && values.comment.length > 2000) {
    errors.push({ field: "comment", message: "Comment must be under 2000 characters." });
  }
  return errors;
}
