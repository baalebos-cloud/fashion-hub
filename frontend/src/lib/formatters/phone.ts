/** Lightweight phone formatting/validation for display purposes.
 * Server-side validation (backend/app/utils/validators.py) is
 * authoritative; this exists only to make numbers easier to read in the
 * UI, e.g. in ProfileForm and delivery contact details. */
export function formatPhoneForDisplay(phone: string): string {
  const digits = phone.replace(/[^\d+]/g, "");
  if (digits.startsWith("+234") && digits.length === 14) {
    return `${digits.slice(0, 4)} ${digits.slice(4, 7)} ${digits.slice(7, 10)} ${digits.slice(10)}`;
  }
  return phone;
}

export function isLikelyValidPhone(phone: string): boolean {
  return /^\+?[1-9]\d{7,14}$/.test(phone.replace(/\s/g, ""));
}
