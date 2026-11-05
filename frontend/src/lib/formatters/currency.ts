/** Currency formatting. Amounts arrive from the backend as plain numbers
 * (already rounded server-side via app/utils/currency.py); this file only
 * handles display, never rounding logic that could drift from the
 * backend's authoritative totals. */
export function formatCurrency(amount: number, currency: string = "NGN", locale = "en-NG"): string {
  try {
    // Whole amounts drop the ".00" (₦86,000); real kobo/cents are always shown (₦86,000.50).
    const whole = Number.isInteger(Math.round(amount * 100) / 100);
    return new Intl.NumberFormat(locale, {
      style: "currency", currency,
      minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    // Unsupported currency code — fall back to a plain prefixed number
    // rather than throwing in a render path.
    return `${currency} ${amount.toFixed(2)}`;
  }
}

/** Whole-naira display for fares and quick prices, e.g. ₦2,100. */
export function formatNaira(amount: number): string {
  return "₦" + Math.round(amount).toLocaleString("en-NG");
}
