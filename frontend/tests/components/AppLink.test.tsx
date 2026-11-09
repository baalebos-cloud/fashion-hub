import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routeObjects } from "@/router";
import { useAuthStore } from "@/store/auth.store";
import type { User } from "@/types/user";

beforeEach(() => useAuthStore.setState({ user: null, isAuthenticated: false, isInitializing: false }));
afterEach(cleanup);

function open(path: string) {
  const router = createMemoryRouter(routeObjects, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

const where = (router: ReturnType<typeof open>) => router.state.location.pathname + router.state.location.search;

describe("the /app/ link", () => {
  it("sends a signed-out visitor to sign in", async () => {
    const router = open("/app/");
    await waitFor(() => expect(where(router)).toBe("/login"));
  });

  it("sends a signed-in person to their dashboard", async () => {
    useAuthStore.setState({ user: { id: "u1", role: "vendor" } as User, isAuthenticated: true });
    const router = open("/app");
    await waitFor(() => expect(where(router)).toBe("/app/vendor"));
  });

  it.each([
    ["/app/reset-password?token=abc", "/reset-password?token=abc"],
    ["/app/verify-email?token=abc", "/verify-email?token=abc"],
    ["/app/login", "/login"],
    ["/app/track/tok123", "/track/tok123"],
    ["/app/s/kemi-couture", "/s/kemi-couture"],
  ])("forwards emailed links built from …/app: %s", async (from, to) => {
    const router = open(from);
    await waitFor(() => expect(where(router)).toBe(to));
  });

  it("forwards a doubled /app/app/ link", async () => {
    useAuthStore.setState({ user: { id: "u1", role: "customer" } as User, isAuthenticated: true });
    const router = open("/app/app/customer/payment/success?ref=1");
    await waitFor(() => expect(where(router)).toBe("/app/customer/payment/success?ref=1"));
  });

  it("still shows Page not found for addresses that don't exist", async () => {
    open("/app/nothing-here");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
  });
});
