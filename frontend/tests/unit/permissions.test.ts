import { describe, expect, it } from "vitest";
import { canMarkOrderReceived } from "@/lib/auth/permissions";
import type { User } from "@/types/user";

const baseUser: User = {
  id: "user-1",
  email: "a@example.com",
  full_name: "A",
  role: "customer",
  is_email_verified: true,
  is_phone_verified: true,
  timezone: "UTC",
};

describe("canMarkOrderReceived", () => {
  const orderId = { status: "delivered", buyer_user_id: "user-1" };

  it("is true for the order's own buyer viewing a delivered order", () => {
    expect(canMarkOrderReceived(baseUser, orderId)).toBe(true);
  });

  it("is false for a different user, even with the same role", () => {
    const otherUser: User = { ...baseUser, id: "user-2" };
    expect(canMarkOrderReceived(otherUser, orderId)).toBe(false);
  });

  it("is true for a professional who is the buyer on a vendor order", () => {
    const tailor: User = { ...baseUser, id: "user-9", role: "tailor" };
    expect(canMarkOrderReceived(tailor, { status: "delivered", buyer_user_id: "user-9" })).toBe(true);
  });

  it("is false before the order is delivered", () => {
    expect(canMarkOrderReceived(baseUser, { status: "shipped", buyer_user_id: "user-1" })).toBe(false);
  });
});
