/** Currency formatting. Amounts arrive from the backend as plain numbers
 * (already rounded server-side via app/utils/currency.py); this file only
 * handles display, never rounding logic that could drift from the
 * backend's authoritative totals. */
export function formatCurrency(amount: number, currency: string = "NGN", locale = "en-NG"): string {
  try {
    return new Intl.NumberFormat(locale, { style: "currency", currency }).format(amount);
  } catch {
    // Unsupported currency code — fall back to a plain prefixed number
    // rather than throwing in a render path.
    return `${currency} ${amount.toFixed(2)}`;
  }
}
