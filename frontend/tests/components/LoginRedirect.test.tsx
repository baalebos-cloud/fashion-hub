import { afterEach, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { LoginForm } from "@/components/auth/LoginForm";

vi.mock("@/hooks/use-auth", () => ({ useAuth: () => ({ logIn: vi.fn().mockResolvedValue({ role: "customer" }) }) }));
afterEach(cleanup);
function Destination() {
  const location = useLocation();
  return <p>{location.pathname + location.search}</p>;
}
it("preserves the payment reference when login is needed on return", async () => {
  render(<MemoryRouter initialEntries={[{ pathname: "/login", state: { from: { pathname: "/app/customer/payment/success", search: "?reference=saved-reference" } } }]}>
    <Routes><Route path="/login" element={<LoginForm />} /><Route path="/app/customer/payment/success" element={<Destination />} /></Routes>
  </MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: "customer@example.com" } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Password123" } });
  fireEvent.submit(screen.getByRole("button", { name: "Log in" }).closest("form")!);
  await screen.findByText("/app/customer/payment/success?reference=saved-reference");
});
