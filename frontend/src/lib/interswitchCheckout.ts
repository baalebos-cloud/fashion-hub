/** Pure, opt-in Interswitch Web Redirect preparation.
 * The backend must generate and persist this checkout payload for an
 * authenticated order; do not construct a payable amount in the browser.
 */
export type InterswitchCheckout = {
  action_url: string;
  fields: Record<string, string>;
};

const ALLOWED_ACTIONS = new Set([
  "https://newwebpay-sandbox.interswitchng.com/collections/w/pay",
  "https://newwebpay.interswitchng.com/collections/w/pay",
]);
const REQUIRED = ["merchant_code", "pay_item_id", "txn_ref",
  "amount", "currency", "cust_email", "site_redirect_url"] as const;

/** Reject tampered provider targets and incomplete backend checkout payloads. */
export function validateInterswitchCheckout(checkout: InterswitchCheckout): void {
  if (!checkout || !ALLOWED_ACTIONS.has(checkout.action_url)) {
    throw new Error("Untrusted Interswitch checkout URL");
  }
  if (!checkout.fields || REQUIRED.some((key) =>
    typeof checkout.fields[key] !== "string" || !checkout.fields[key].trim()
  )) {
    throw new Error("Incomplete Interswitch checkout request");
  }
  if (!/^[1-9]\d*$/.test(checkout.fields.amount) ||
      checkout.fields.currency !== "566" ||
      !/^[A-Za-z0-9_-]{1,128}$/.test(checkout.fields.txn_ref)) {
    throw new Error("Invalid NGN checkout amount or reference");
  }
  const callback = new URL(checkout.fields.site_redirect_url);
  if (callback.protocol !== "https:" || callback.username || callback.password) {
    throw new Error("Untrusted checkout return URL");
  }
}

/** Render a real HTML POST form, then submit it on direct user action only.
 * Never interpret a return POST or query parameter as proof of payment.
 */
export function submitInterswitchCheckout(checkout: InterswitchCheckout): void {
  validateInterswitchCheckout(checkout);
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkout.action_url;
  form.style.display = "none";
  for (const [name, value] of Object.entries(checkout.fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}
