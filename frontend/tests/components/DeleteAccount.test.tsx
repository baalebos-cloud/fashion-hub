import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DeleteAccount } from "@/components/account/DeleteAccount";
import { ToastProvider } from "@/components/ui/toast";
import { usersApi } from "@/api/users.api";
import { useAuthStore } from "@/store/auth.store";

vi.mock("@/api/users.api", () => ({ usersApi: { deletionStatus: vi.fn(), deleteAccount: vi.fn() } }));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

const logOut = vi.fn().mockResolvedValue(undefined);
beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ logOut });
});
afterEach(cleanup);

const renderIt = () => render(
  <ToastProvider>
    <MemoryRouter initialEntries={["/app/settings"]}>
      <Routes>
        <Route path="/app/settings" element={<DeleteAccount />} />
        <Route path="/" element={<p>home page</p>} />
      </Routes>
    </MemoryRouter>
  </ToastProvider>);

describe("delete account", () => {
  it("asks for the password, deletes, signs out and goes home", async () => {
    vi.mocked(usersApi.deletionStatus).mockResolvedValue({ can_delete: true, blockers: [] });
    vi.mocked(usersApi.deleteAccount).mockResolvedValue();
    renderIt();
    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));
    expect(await screen.findByRole("dialog", { name: "Delete your account?" })).toBeTruthy();
    const submit = screen.getByRole("button", { name: "Delete my account" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("Enter your password to confirm"), { target: { value: "my-password" } });
    fireEvent.click(submit);
    expect(await screen.findByText("home page")).toBeTruthy();
    expect(usersApi.deleteAccount).toHaveBeenCalledWith("my-password");
    expect(logOut).toHaveBeenCalled();
    expect(screen.getByText("Your account has been deleted.")).toBeTruthy();
  });

  it("shows a wrong password and stays signed in", async () => {
    vi.mocked(usersApi.deletionStatus).mockResolvedValue({ can_delete: true, blockers: [] });
    vi.mocked(usersApi.deleteAccount).mockRejectedValue(new Error("That password isn't right."));
    renderIt();
    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));
    fireEvent.change(await screen.findByLabelText("Enter your password to confirm"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Delete my account" }));
    expect(await screen.findByText("That password isn't right.")).toBeTruthy();
    expect(logOut).not.toHaveBeenCalled();
  });

  it("explains what has to finish first instead of asking for the password", async () => {
    vi.mocked(usersApi.deletionStatus).mockResolvedValue({
      can_delete: false, blockers: ["You have 2 open orders. Finish or cancel them first."],
    });
    renderIt();
    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));
    expect(await screen.findByRole("dialog", { name: "You can't delete your account yet" })).toBeTruthy();
    expect(screen.getByText("You have 2 open orders. Finish or cancel them first.")).toBeTruthy();
    expect(screen.queryByLabelText("Enter your password to confirm")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "OK" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(usersApi.deleteAccount).not.toHaveBeenCalled();
  });
});
