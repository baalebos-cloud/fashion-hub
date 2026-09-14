import { describe, expect, it } from "vitest";
import { endpoints } from "@/lib/api/endpoints";

/** Regression guard: the required order endpoint surface must stay exact. */
describe("orders endpoints", () => {
  it("matches the required backend endpoint surface exactly", () => {
    const id = "abc-123";
    expect(endpoints.orders.list).toBe("/orders");
    expect(endpoints.orders.details(id)).toBe(`/orders/${id}`);
    expect(endpoints.orders.accept(id)).toBe(`/orders/${id}/accept`);
    expect(endpoints.orders.startProduction(id)).toBe(`/orders/${id}/start-production`);
    expect(endpoints.orders.ready(id)).toBe(`/orders/${id}/ready`);
    expect(endpoints.orders.ship(id)).toBe(`/orders/${id}/ship`);
    expect(endpoints.orders.tracking(id)).toBe(`/orders/${id}/tracking`);
    expect(endpoints.orders.received(id)).toBe(`/orders/${id}/received`);
    expect(endpoints.orders.timeline(id)).toBe(`/orders/${id}/timeline`);
    expect(endpoints.orders.review(id)).toBe(`/orders/${id}/review`);
  });
});
