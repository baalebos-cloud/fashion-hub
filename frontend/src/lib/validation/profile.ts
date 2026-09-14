import type { FieldError } from "./auth";
import { isLikelyValidPhone } from "@/lib/formatters/phone";

export function validateProfile(values: { fullName: string; phoneNumber?: string }): FieldError[] {
  const errors: FieldError[] = [];
  if (values.fullName.trim().length < 2) {
    errors.push({ field: "fullName", message: "Enter your full name." });
  }
  if (values.phoneNumber && !isLikelyValidPhone(values.phoneNumber)) {
    errors.push({ field: "phoneNumber", message: "Enter a valid phone number." });
  }
  return errors;
}
