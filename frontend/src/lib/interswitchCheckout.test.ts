import { describe, expect, it } from "vitest";
import { validateInterswitchCheckout, type InterswitchCheckout } from "./interswitchCheckout";

function checkout(): InterswitchCheckout {
  return {
    action_url: "https://newwebpay-sandbox.interswitchng.com/collections/w/pay",
    fields: {
      merchant_code: "MX_TEST",
      pay_item_id: "ITEM_TEST",
      txn_ref: "order_123",
      amount: "25050",
      currency: "566",
      cust_email: "buyer@example.com",
      site_redirect_url: "https://example.com/payment-result",
    },
  };
}

describe("Interswitch POST checkout protection", () => {
  it("accepts a complete backend-issued checkout payload", () => {
    expect(() => validateInterswitchCheckout(checkout())).not.toThrow();
  });

  it.each([
    ["unknown host", (v: InterswitchCheckout) => { v.action_url = "https://evil.example/pay"; }],
    ["empty merchant", (v: InterswitchCheckout) => { v.fields.merchant_code = ""; }],
    ["zero amount", (v: InterswitchCheckout) => { v.fields.amount = "0"; }],
    ["fractional amount", (v: InterswitchCheckout) => { v.fields.amount = "1.2"; }],
    ["wrong currency", (v: InterswitchCheckout) => { v.fields.currency = "840"; }],
    ["unsafe reference", (v: InterswitchCheckout) => { v.fields.txn_ref = "../order"; }],
    ["insecure callback", (v: InterswitchCheckout) => { v.fields.site_redirect_url = "http://example.com"; }],
  ])("rejects %s", (_name, mutate) => {
    const request = checkout();
    mutate(request);
    expect(() => validateInterswitchCheckout(request)).toThrow();
  });
});
