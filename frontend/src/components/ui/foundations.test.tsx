import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { SkeletonRows } from "@/components/ui/skeleton";

afterEach(() => { cleanup(); vi.useRealTimers(); });

describe("UI foundations", () => {
  it("primary buttons use the indigo action colour and meet the 44px target", () => {
    render(<Button>Send order</Button>);
    const button = screen.getByRole("button", { name: "Send order" });
    expect(button.className).toContain("bg-indigo");
    expect(button.className).toContain("min-h-11");
  });

  it("loading buttons are disabled and announce they are busy", () => {
    render(<Button isLoading>Saving</Button>);
    const button = screen.getByRole("button", { name: /Saving/ });
    expect(button).toHaveProperty("disabled", true);
    expect(button.getAttribute("aria-busy")).toBe("true");
  });

  it("status badges carry a word and a semantic tone", () => {
    render(<Badge tone="success">Delivered</Badge>);
    const badge = screen.getByText("Delivered");
    expect(badge.className).toContain("bg-success-wash");
    expect(badge.className).toContain("text-success");
  });

  it("fields wire the label and show the error instead of the help text", () => {
    render(
      <Field label="Phone number" htmlFor="phone" help="11 digits" error="Enter all 11 digits">
        <Input id="phone" error="Enter all 11 digits" aria-describedby="phone-hint" />
      </Field>,
    );
    const input = screen.getByLabelText("Phone number");
    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(screen.getByRole("alert").textContent).toBe("Enter all 11 digits");
    expect(screen.queryByText("11 digits")).toBeNull();
  });

  it("error states explain the problem and retry", () => {
    const retry = vi.fn();
    render(<ErrorState title="Couldn't load your orders" description="Check your connection." onRetry={retry} />);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("loading rows say so on slow connections and offer a retry", () => {
    vi.useFakeTimers();
    const retry = vi.fn();
    render(<SkeletonRows rows={2} label="Loading orders" onRetry={retry} />);
    expect(screen.getByRole("status", { name: "Loading orders" })).toBeTruthy();
    expect(screen.queryByText("Still loading…")).toBeNull();
    act(() => { vi.advanceTimersByTime(8000); });
    expect(screen.getByText("Still loading…")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
