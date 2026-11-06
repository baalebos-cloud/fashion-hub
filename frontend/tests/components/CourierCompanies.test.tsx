import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CourierCompanies } from "@/components/dispatch/CourierCompanies";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({ apiClient: { get: vi.fn(), post: vi.fn() } }));
vi.mock("@/lib/utils/errors", () => ({ getDisplayErrorMessage: (_e: unknown, f: string) => f }));
afterEach(cleanup);

describe("courier companies", () => {
  it("shows prices and books the chosen courier with a reason", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [
      { courier: "sandbox", name: "Sandbox Courier (test only)", available: true, quote_id: "sbxq_r1_4500", amount_ngn: 4500, eta_minutes: 50 },
      { courier: "far", name: "Far Courier", available: false, reason: "farther than 60 km" },
    ] });
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
    const onBooked = vi.fn();
    render(<CourierCompanies requestId="r1" onBooked={onBooked} />);
    fireEvent.click(screen.getByRole("button", { name: "Courier companies" }));
    expect(await screen.findByText(/~50 min/)).toBeTruthy();
    expect(screen.getByText("farther than 60 km")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Book" }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "No riders free nearby" } });
    fireEvent.click(screen.getByRole("button", { name: "Book Sandbox Courier (test only)" }));
    await waitFor(() => expect(apiClient.post).toHaveBeenCalledWith("/admin/dispatch/requests/r1/courier-booking",
      { courier: "sandbox", quote_id: "sbxq_r1_4500", reason: "No riders free nearby" }));
    expect(onBooked).toHaveBeenCalled();
  });
});
