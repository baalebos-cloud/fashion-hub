import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import AdminLogin from "@/pages/auth/AdminLogin";
import Security from "@/pages/admin/Security";
import { describeDevice } from "@/lib/utils/device";
import { authApi } from "@/api/auth.api";
import { adminSecurityApi } from "@/api/admin-security.api";
import { useAuthStore } from "@/store/auth.store";
import { ApiError } from "@/lib/api/errors";

vi.mock("@/api/auth.api", () => ({ authApi: { adminLogIn: vi.fn(), adminVerify: vi.fn() } }));
vi.mock("@/api/admin-security.api", () => ({
  adminSecurityApi: { activity: vi.fn(), summary: vi.fn(), footprint: vi.fn(), auditLogs: vi.fn() },
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

const renderLogin = () => render(
  <MemoryRouter initialEntries={["/admin/login"]}>
    <Routes>
      <Route path="/admin/login" element={<AdminLogin />} />
      <Route path="/app/admin" element={<p>admin home</p>} />
    </Routes>
  </MemoryRouter>);

describe("admin sign-in", () => {
  it("sets up the authenticator on first use, then signs in with a code", async () => {
    vi.mocked(authApi.adminLogIn).mockResolvedValue({
      step: "enroll", challenge: "c".repeat(40), secret: "JBSWY3DPEHPK3PXP",
      otpauth_uri: "otpauth://totp/Tailora%20Admin:me?secret=JBSWY3DPEHPK3PXP&issuer=Tailora%20Admin",
    });
    vi.mocked(authApi.adminVerify).mockResolvedValue({ access_token: "a", refresh_token: "r", token_type: "bearer" });
    const completeSignIn = vi.fn().mockResolvedValue({ id: "u1", role: "admin" });
    useAuthStore.setState({ completeSignIn });
    renderLogin();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "me@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect(await screen.findByText("Set up your authenticator")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Authenticator setup QR code" }).innerHTML).toContain("<svg");
    expect(screen.getByTestId("totp-secret").textContent).toBe("JBSWY3DPEHPK3PXP");
    fireEvent.change(screen.getByLabelText("Six-digit code"), { target: { value: "12a3456" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("admin home")).toBeTruthy();
    expect(authApi.adminVerify).toHaveBeenCalledWith("c".repeat(40), "123456");
    expect(completeSignIn).toHaveBeenCalled();
    // Removed by the login page's effect cleanup, which can run just after the next page renders.
    await waitFor(() => expect(document.querySelector('meta[name="robots"]')).toBeNull());
  });

  it("shows one generic message for any wrong detail", async () => {
    vi.mocked(authApi.adminLogIn).mockRejectedValue(new ApiError("Invalid email, password or code.", "UNAUTHORIZED", 401, null));
    renderLogin();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "me@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Invalid email, password or code.");
  });
});

describe("security page", () => {
  it("summarises activity and lets the admin drill into a person and an IP", async () => {
    vi.mocked(adminSecurityApi.summary).mockResolvedValue({
      active_now: 3, sign_ins_24h: 12, failed_sign_ins_24h: 4, admin_sign_ins_24h: 1, distinct_ips_24h: 9,
      top_failed_ips: [{ ip_address: "6.6.6.6", attempts: 4 }], retention_days: 180,
    });
    vi.mocked(adminSecurityApi.activity).mockResolvedValue([
      { id: "1", at: new Date().toISOString(), event: "sign_in", user_id: "u1", user_name: "Kemi Couture", user_email: "kemi@example.com",
        role: "tailor", method: "POST", path: "/api/v1/auth/login", status_code: 200, ip_address: "102.89.4.20",
        device_id: "web-1234567890abcdef1234", user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Safari/604.1", details: {} },
      { id: "2", at: new Date().toISOString(), event: "sign_in_failed", user_id: null, user_name: null, user_email: null,
        role: null, method: "POST", path: "/api/v1/auth/login", status_code: 401, ip_address: "6.6.6.6",
        device_id: null, user_agent: null, details: { email: "kemi@example.com" } },
    ]);
    vi.mocked(adminSecurityApi.footprint).mockResolvedValue({
      user: { id: "u1", name: "Kemi Couture", email: "kemi@example.com", role: "tailor", is_active: true },
      ips: [{ value: "102.89.4.20", first_seen: new Date().toISOString(), last_seen: new Date().toISOString(), events: 7 }],
      devices: [],
    });
    render(<Security />);
    expect(await screen.findByText("Tried kemi@example.com")).toBeTruthy();
    expect(screen.getByText("Safari on iPhone/iPad")).toBeTruthy();
    expect(screen.getByText("Failed sign-ins (24 h)").nextSibling?.textContent).toBe("4");
    fireEvent.click(screen.getByRole("button", { name: "Kemi Couture" }));
    expect(await screen.findByText(/7 events/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "6.6.6.6 · 4" }));
    await waitFor(() => expect(adminSecurityApi.activity).toHaveBeenLastCalledWith({ ip: "6.6.6.6" }));
  });

  it("names common devices from the browser string", () => {
    expect(describeDevice("Mozilla/5.0 (Windows NT 10.0) Chrome/120.0 Safari/537.36")).toBe("Chrome on Windows");
    expect(describeDevice("Mozilla/5.0 (Linux; Android 14) Chrome/120.0 Mobile Safari/537.36")).toBe("Chrome on Android");
    expect(describeDevice(null)).toBe("Unknown device");
  });
});
