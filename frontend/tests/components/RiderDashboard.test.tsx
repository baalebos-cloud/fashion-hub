import { beforeEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "@/pages/delivery/Dashboard";
import { deliveriesApi } from "@/api/deliveries.api";
import type { Delivery } from "@/types/delivery";

vi.mock("@/api/deliveries.api", () => ({ deliveriesApi: { myHistory: vi.fn() } }));
vi.mock("@/api/dashboard.api", () => ({ dashboardApi: { getSummary: vi.fn().mockResolvedValue([]) } }));
vi.mock("@/api/delivery-partners.api", () => ({ deliveryPartnersApi: { activeDeliveries: vi.fn().mockResolvedValue([]) } }));
vi.mock("@/components/delivery/RiderStatusCard", () => ({ RiderStatusCard: () => null }));
vi.mock("@/components/delivery/RiderRoute", () => ({ RiderRoute: () => null }));
vi.mock("@/components/common/Greeting", () => ({ Greeting: () => null }));

const done = (id: string, status: Delivery["status"] = "delivered"): Delivery => ({
  id, order_id: `${id}aaaaaaaaaa`, status, delivery_fee: 2000, delivered_at: status === "delivered" ? "2026-11-15T13:14:00Z" : null,
});

beforeEach(() => vi.clearAllMocks());

it("lists the rider's last five finished jobs with a link to the full history", async () => {
  vi.mocked(deliveriesApi.myHistory).mockResolvedValue([done("job00001"), done("job00002", "cancelled")]);
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  expect(await screen.findByText("Order JOB00001")).toBeTruthy();
  expect(screen.getByText("Order JOB00002")).toBeTruthy();
  expect(screen.getByText("₦2,000")).toBeTruthy();
  expect(screen.getByText("No fare")).toBeTruthy(); // the cancelled job wasn't paid
  expect(screen.getByRole("link", { name: "See all" }).getAttribute("href")).toBe("/app/delivery/history");
  expect(vi.mocked(deliveriesApi.myHistory)).toHaveBeenCalledWith(1, 5);
});

it("says so when the rider hasn't finished a job yet", async () => {
  vi.mocked(deliveriesApi.myHistory).mockResolvedValue([]);
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  expect(await screen.findByText(/Jobs you finish show up here/)).toBeTruthy();
  expect(screen.queryByRole("link", { name: "See all" })).toBeNull();
});

it("hides the section instead of claiming no jobs when loading fails", async () => {
  vi.mocked(deliveriesApi.myHistory).mockRejectedValue(new Error("offline"));
  render(<MemoryRouter><Dashboard /></MemoryRouter>);
  await screen.findByText("Current job");
  await Promise.resolve();
  expect(screen.queryByText("Recently completed")).toBeNull();
});
