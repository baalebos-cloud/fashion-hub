import type { FieldError } from "./auth";
import { isLikelyValidPhone } from "@/lib/formatters/phone";

/** Names are checked by validateNameParts (lib/names.ts). */
export function validateProfile(values: { phoneNumber?: string }): FieldError[] {
  const errors: FieldError[] = [];
  if (values.phoneNumber && !isLikelyValidPhone(values.phoneNumber)) {
    errors.push({ field: "phoneNumber", message: "Enter a valid phone number." });
  }
  return errors;
}
