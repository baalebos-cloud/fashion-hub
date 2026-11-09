import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PaymentAppReturn from "@/pages/public/PaymentAppReturn";
import { appReturnLink, paymentCallbackUrl } from "@/lib/payments/return-url";
import { internalPath } from "@/lib/native/app-shell";

const native = vi.hoisted(() => ({ app: false }));
vi.mock("@/lib/native/platform", () => ({ isNativeApp: () => native.app, nativePlatform: () => (native.app ? "ios" : "web") }));
afterEach(() => { cleanup(); native.app = false; });

describe("where the payment provider sends people back", () => {
  it("returns to this site's result page on the website", () => {
    expect(paymentCallbackUrl("customer")).toBe(`${window.location.origin}/app/customer/payment/success`);
    expect(paymentCallbackUrl("vendor")).toBe(`${window.location.origin}/app/professional/vendor-payment/success`);
  });

  it("returns through the website's hand-back page in the phone app", () => {
    native.app = true;
    expect(paymentCallbackUrl("customer")).toBe("https://fashion-hub-tawny.vercel.app/payment/app-return?for=customer");
  });

  it("builds the app link with only the payment reference, landing on the right page", () => {
    const link = appReturnLink("customer", new URLSearchParams("for=customer&trxref=T123_ab&reference=T123_ab"));
    expect(link).toBe("tailora://app/customer/payment/success?reference=T123_ab");
    expect(internalPath(link!)).toBe("/app/customer/payment/success?reference=T123_ab");
    expect(appReturnLink("vendor", new URLSearchParams("reference=R9"))).toBe("tailora://app/professional/vendor-payment/success?reference=R9");
    expect(appReturnLink("customer", new URLSearchParams("reference=<script>"))).toBe("tailora://app/customer/payment/success");
    expect(appReturnLink("admin", new URLSearchParams("reference=R9"))).toBeNull();
  });
});

describe("hand-back page", () => {
  it("offers a button back into the app", () => {
    render(<MemoryRouter initialEntries={["/payment/app-return?for=customer&reference=T1"]}><PaymentAppReturn /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Payment finished" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Return to the Tailora app" }).getAttribute("href"))
      .toBe("tailora://app/customer/payment/success?reference=T1");
  });
});
