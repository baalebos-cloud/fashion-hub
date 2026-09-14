import type { FieldError } from "./auth";

export function validateCheckout(values: { deliveryAddressId?: string }): FieldError[] {
  const errors: FieldError[] = [];
  if (!values.deliveryAddressId) {
    errors.push({ field: "deliveryAddressId", message: "Select a delivery address to continue." });
  }
  return errors;
}
