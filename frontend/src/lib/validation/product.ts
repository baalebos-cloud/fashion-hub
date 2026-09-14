import type { FieldError } from "./auth";

export function validateProduct(values: { name: string; basePrice: number }): FieldError[] {
  const errors: FieldError[] = [];
  if (!values.name.trim()) errors.push({ field: "name", message: "Product name is required." });
  if (values.basePrice <= 0) errors.push({ field: "basePrice", message: "Price must be greater than zero." });
  return errors;
}
