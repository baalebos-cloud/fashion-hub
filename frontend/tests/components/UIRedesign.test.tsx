import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "@/pages/public/Home";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";
import { SignupForm } from "@/components/auth/SignupForm";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Footer } from "@/components/layout/Footer";

afterEach(cleanup);

// ─── Shared mocks ────────────────────────────────────────────────────────────
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: null,
    logIn: vi.fn(),
    signUp: vi.fn(),
    logOut: vi.fn(),
  }),
}));
vi.mock("@/hooks/use-notifications", () => ({
  useNotifications: () => ({ unreadCount: 0 }),
}));
vi.mock("@/lib/validation/auth", () => ({
  validateLogIn: () => [],
  validateSignUp: () => [],
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (_err: unknown, fallback: string) => fallback,
}));

function wrap(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ─── Home ─────────────────────────────────────────────────────────────────────
describe("Home page", () => {
  it("renders the hero headline", () => {
    wrap(<Home />);
    expect(screen.getByRole("heading", { level: 1 })).toBeTruthy();
    expect(screen.getByText(/know their craft/i)).toBeTruthy();
  });

  it("renders Find a tailor and Join as a professional CTAs", () => {
    wrap(<Home />);
    expect(screen.getByRole("link", { name: /find a tailor/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /join as a professional/i })).toBeTruthy();
  });

  it("renders the How it works section with 3 steps", () => {
    wrap(<Home />);
    expect(screen.getByText(/how it works/i)).toBeTruthy();
    expect(screen.getByText(/find your tailor/i)).toBeTruthy();
    expect(screen.getByText(/order with confidence/i)).toBeTruthy();
    expect(screen.getByText(/track every step/i)).toBeTruthy();
  });

  it("renders testimonials section", () => {
    wrap(<Home />);
    expect(screen.getByText(/what people are saying/i)).toBeTruthy();
    expect(screen.getAllByRole("blockquote").length).toBeGreaterThanOrEqual(3);
  });

  it("renders the CTA banner with Get started link", () => {
    wrap(<Home />);
    expect(screen.getByRole("link", { name: /get started/i })).toBeTruthy();
  });
});

// ─── AuthLayout ───────────────────────────────────────────────────────────────
describe("AuthLayout", () => {
  it("renders children inside the form panel", () => {
    wrap(<AuthLayout><p>Test child content</p></AuthLayout>);
    expect(screen.getByText("Test child content")).toBeTruthy();
  });

  it("renders the brand quote in the decorative panel", () => {
    wrap(<AuthLayout><span /></AuthLayout>);
    expect(screen.getByText(/craft of tailoring/i)).toBeTruthy();
  });
});

// ─── LoginForm ────────────────────────────────────────────────────────────────
describe("LoginForm", () => {
  it("renders email and password fields with correct labels", () => {
    wrap(<LoginForm />);
    expect(screen.getByLabelText("Email address")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
  });

  it("renders Sign in button", () => {
    wrap(<LoginForm />);
    expect(screen.getByRole("button", { name: /sign in/i })).toBeTruthy();
  });

  it("renders Forgot password link", () => {
    wrap(<LoginForm />);
    expect(screen.getByRole("link", { name: /forgot password/i })).toBeTruthy();
  });

  it("renders Create one signup link", () => {
    wrap(<LoginForm />);
    expect(screen.getByRole("link", { name: /create one/i })).toBeTruthy();
  });

  it("toggles password visibility when eye button is clicked", () => {
    wrap(<LoginForm />);
    const passwordInput = screen.getByLabelText("Password") as HTMLInputElement;
    expect(passwordInput.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: /show password/i }));
    expect(passwordInput.type).toBe("text");
    fireEvent.click(screen.getByRole("button", { name: /hide password/i }));
    expect(passwordInput.type).toBe("password");
  });

  it("calls logIn with email and password on submit", async () => {
    const logIn = vi.fn().mockResolvedValue({ role: "customer" });
    vi.doMock("@/hooks/use-auth", () => ({ useAuth: () => ({ user: null, logIn, signUp: vi.fn(), logOut: vi.fn() }) }));
    wrap(<LoginForm />);
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Password123" } });
    fireEvent.submit(screen.getByRole("button", { name: /sign in/i }).closest("form")!);
  });
});

// ─── SignupForm ───────────────────────────────────────────────────────────────
describe("SignupForm", () => {
  it("renders all required fields", () => {
    wrap(<SignupForm />);
    expect(screen.getByLabelText("Full name")).toBeTruthy();
    expect(screen.getByLabelText("Email address")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
  });

  it("renders role picker with 5 options", () => {
    wrap(<SignupForm />);
    const radios = screen.getAllByRole("radio");
    expect(radios.length).toBe(5);
  });

  it("renders Create account button", () => {
    wrap(<SignupForm />);
    expect(screen.getByRole("button", { name: /create account/i })).toBeTruthy();
  });

  it("renders Sign in link", () => {
    wrap(<SignupForm />);
    expect(screen.getByRole("link", { name: /sign in/i })).toBeTruthy();
  });

  it("selecting a role radio updates selection", () => {
    wrap(<SignupForm />);
    const tailorRadio = screen.getByRole("radio", { name: /tailor/i });
    fireEvent.click(tailorRadio);
    expect((tailorRadio as HTMLInputElement).checked).toBe(true);
  });

  it("toggles password visibility", () => {
    wrap(<SignupForm />);
    const passwordInput = screen.getByLabelText("Password") as HTMLInputElement;
    expect(passwordInput.type).toBe("password");
    fireEvent.click(screen.getByRole("button", { name: /show password/i }));
    expect(passwordInput.type).toBe("text");
  });

  it("shows referral code banner when ref param is present", () => {
    render(
      <MemoryRouter initialEntries={["/signup?ref=TESTCODE"]}>
        <SignupForm />
      </MemoryRouter>
    );
    expect(screen.getByText("TESTCODE")).toBeTruthy();
  });
});

// ─── Header ───────────────────────────────────────────────────────────────────
describe("Header (unauthenticated)", () => {
  it("renders the brand name", () => {
    wrap(<Header />);
    expect(screen.getByText("Tailora")).toBeTruthy();
  });

  it("renders public nav links on desktop", () => {
    wrap(<Header />);
    expect(screen.getByRole("link", { name: /find a tailor/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /marketplace/i })).toBeTruthy();
  });

  it("renders Get started CTA", () => {
    wrap(<Header />);
    expect(screen.getByRole("link", { name: /get started/i })).toBeTruthy();
  });

  it("toggles mobile menu on hamburger click", () => {
    wrap(<Header />);
    const toggle = screen.getByRole("button", { name: /open menu/i });
    fireEvent.click(toggle);
    expect(screen.getByRole("button", { name: /close menu/i })).toBeTruthy();
    expect(screen.getByRole("navigation", { name: /mobile navigation/i })).toBeTruthy();
  });
});

// ─── Sidebar ──────────────────────────────────────────────────────────────────
describe("Sidebar", () => {
  it("renders customer nav items", () => {
    wrap(<Sidebar role="customer" />);
    expect(screen.getByRole("link", { name: /overview/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /orders/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /measurements/i })).toBeTruthy();
  });

  it("renders tailor nav with Materials group heading", () => {
    wrap(<Sidebar role="tailor" />);
    expect(screen.getByText("Materials")).toBeTruthy();
    expect(screen.getByRole("link", { name: /marketplace/i })).toBeTruthy();
  });

  it("renders admin nav with Verification group heading", () => {
    wrap(<Sidebar role="admin" />);
    expect(screen.getByText("Verification")).toBeTruthy();
    expect(screen.getByRole("link", { name: /kyc/i })).toBeTruthy();
  });

  it("calls onNavigate when a link is clicked", () => {
    const onNavigate = vi.fn();
    wrap(<Sidebar role="customer" mobile onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("link", { name: /overview/i }));
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });
});

// ─── Footer ───────────────────────────────────────────────────────────────────
describe("Footer", () => {
  it("renders brand name and tagline", () => {
    wrap(<Footer />);
    expect(screen.getByRole("link", { name: "Tailora" })).toBeTruthy();
    expect(screen.getByText(/nigeria's marketplace/i)).toBeTruthy();
  });

  it("renders Platform, Company, and Legal link groups", () => {
    wrap(<Footer />);
    expect(screen.getByText("Platform")).toBeTruthy();
    expect(screen.getByText("Company")).toBeTruthy();
    expect(screen.getByText("Legal")).toBeTruthy();
  });

  it("renders Terms and Privacy links", () => {
    wrap(<Footer />);
    expect(screen.getByRole("link", { name: "Terms" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Privacy" })).toBeTruthy();
  });

  it("renders copyright notice with current year", () => {
    wrap(<Footer />);
    expect(screen.getByText(new RegExp(String(new Date().getFullYear())))).toBeTruthy();
  });
});
