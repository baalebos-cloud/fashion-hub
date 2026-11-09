import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { LoginForm } from "@/components/auth/LoginForm";
import AdminLogin from "@/pages/auth/AdminLogin";

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({ logIn: vi.fn().mockRejectedValue(new Error("Admin accounts sign in at /admin/login.")) }),
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));
afterEach(cleanup);

it("sends an admin to the two-step sign-in with their email filled in", async () => {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginForm />} />
        <Route path="/admin/login" element={<AdminLogin />} />
      </Routes>
    </MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "admin@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Password123" } });
  fireEvent.submit(screen.getByRole("button", { name: "Sign in" }).closest("form")!);
  fireEvent.click(await screen.findByRole("link", { name: "Go to admin sign-in" }));
  expect(((await screen.findByLabelText("Email address")) as HTMLInputElement).value).toBe("admin@example.com");
});
