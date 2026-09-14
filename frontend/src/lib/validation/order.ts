import type { FieldError } from "./auth";

export function validateCreateOrder(values: { measurementProfileId?: string; itemCount: number }): FieldError[] {
  const errors: FieldError[] = [];
  if (values.itemCount < 1) {
    errors.push({ field: "items", message: "Add at least one item to your order." });
  }
  if (!values.measurementProfileId) {
    errors.push({ field: "measurementProfileId", message: "Select or add a measurement profile." });
  }
  return errors;
}
