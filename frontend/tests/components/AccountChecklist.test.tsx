import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AccountChecklist } from "@/components/profile/AccountChecklist";
import { VerifyEmail } from "@/components/auth/VerifyEmail";
import { authApi } from "@/api/auth.api";
import { useAuthStore } from "@/store/auth.store";
import type { User } from "@/types/user";

vi.mock("@/api/auth.api", () => ({ authApi: { resendVerification: vi.fn(), verifyEmail: vi.fn() } }));
vi.mock("@/components/profile/ProfilePhoto", () => ({ ProfilePhoto: () => <button type="button">Change photo</button> }));

const base = { id: "u1", email: "kemi@example.com", full_name: "Kemi Adeyemi", is_phone_verified: false, timezone: "Africa/Lagos" };
const as = (patch: Partial<User>) => useAuthStore.setState({ user: { ...base, role: "customer", is_email_verified: true, profile_photo_url: null, ...patch } as User });

beforeEach(() => vi.clearAllMocks());
afterEach(() => { cleanup(); useAuthStore.setState({ user: null }); });

describe("account checklist", () => {
  it("asks unconfirmed people to confirm and resends the link", async () => {
    as({ is_email_verified: false });
    vi.mocked(authApi.resendVerification).mockResolvedValue();
    render(<AccountChecklist />);
    expect(screen.getByText(/Confirm your email address/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    expect(await screen.findByText(/New link sent/)).toBeTruthy();
    expect(authApi.resendVerification).toHaveBeenCalledWith("kemi@example.com");
  });

  it("requires a photo from riders, vendors and tailors but not customers", () => {
    for (const role of ["delivery_partner", "vendor", "tailor", "designer"] as const) {
      as({ role });
      const { unmount } = render(<AccountChecklist />);
      expect(screen.getByRole("region", { name: "Profile photo required" })).toBeTruthy();
      unmount();
    }
    as({ role: "customer" });
    const { container } = render(<AccountChecklist />);
    expect(container.textContent).toBe("");
    as({ role: "tailor", profile_photo_url: "/api/v1/media/files/me.jpg" });
    cleanup();
    expect(render(<AccountChecklist />).container.textContent).toBe("");
  });
});

describe("expired confirmation link", () => {
  it("lets the person ask for a new link", async () => {
    vi.mocked(authApi.verifyEmail).mockRejectedValue(new Error("expired"));
    vi.mocked(authApi.resendVerification).mockResolvedValue();
    render(<MemoryRouter initialEntries={["/verify-email?token=old"]}><VerifyEmail /></MemoryRouter>);
    expect(await screen.findByText("This link has expired")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "kemi@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send a new link" }));
    expect(await screen.findByText(/a new link is on its way/)).toBeTruthy();
    expect(authApi.resendVerification).toHaveBeenCalledWith("kemi@example.com");
  });
});
