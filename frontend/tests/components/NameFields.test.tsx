import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { nameParts, composeName, validateNameParts } from "@/lib/names";

const updateProfile = vi.fn();
const refreshUser = vi.fn().mockResolvedValue(undefined);
let currentUser: Record<string, unknown> | null = null;

vi.mock("@/hooks/use-user", () => ({ useUser: () => ({ user: currentUser, isSaving: false, updateProfile }) }));
vi.mock("@/store/auth.store", () => ({ useAuthStore: (pick: (s: unknown) => unknown) => pick({ refreshUser }) }));
vi.mock("@/components/ui/toast", () => ({ useToast: () => ({ showToast: vi.fn() }) }));

import { ProfileForm } from "@/components/profile/ProfileForm";

describe("name helpers", () => {
  it("uses the saved parts, or splits an older full name", () => {
    expect(nameParts({ full_name: "Ifeoma Chidinma Nwosu", first_name: "Ifeoma", middle_name: "Chidinma", last_name: "Nwosu" }))
      .toEqual({ first: "Ifeoma", middle: "Chidinma", last: "Nwosu" });
    expect(nameParts({ full_name: "Ade Bola Chi Okeke" })).toEqual({ first: "Ade", middle: "Bola Chi", last: "Okeke" });
    expect(composeName({ first: " Amaka ", middle: "", last: "Okafor" })).toBe("Amaka Okafor");
  });

  it("needs a first name and surname with letters only", () => {
    expect(validateNameParts({ first: "", middle: "", last: "Okafor" }).first).toBeTruthy();
    expect(validateNameParts({ first: "Amaka", middle: "", last: "" }).last).toBeTruthy();
    expect(validateNameParts({ first: "Am4ka", middle: "", last: "Okafor" }).first).toBeTruthy();
    expect(validateNameParts({ first: "Oluwaseun", middle: "D'Angelo", last: "Adébáyọ̀-Eze" })).toEqual({});
  });
});

describe("ProfileForm name editing", () => {
  beforeEach(() => { updateProfile.mockReset().mockResolvedValue({}); refreshUser.mockClear(); });

  it("shows the current name in three editable fields and saves the parts", async () => {
    currentUser = { id: "u1", role: "vendor", email: "v@example.com", full_name: "Adebayo Balogun" };
    render(<ProfileForm />);
    const first = screen.getByLabelText("First name") as HTMLInputElement;
    expect(first.value).toBe("Adebayo");
    expect((screen.getByLabelText("Surname") as HTMLInputElement).value).toBe("Balogun");
    fireEvent.change(screen.getByLabelText(/Middle name/), { target: { value: "Tunde" } });
    fireEvent.change(screen.getByLabelText("Surname"), { target: { value: "Balogun-Ade" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(updateProfile).toHaveBeenCalledWith(expect.objectContaining(
      { first_name: "Adebayo", middle_name: "Tunde", last_name: "Balogun-Ade" })));
    expect(refreshUser).toHaveBeenCalled();
  });

  it("fills the fields when the account finishes loading after the page opens", () => {
    currentUser = null;
    const { rerender } = render(<ProfileForm />);
    expect((screen.getByLabelText("First name") as HTMLInputElement).value).toBe("");
    currentUser = { id: "u2", role: "customer", email: "c@example.com", full_name: "Amaka Okafor", first_name: "Amaka", last_name: "Okafor" };
    rerender(<ProfileForm />);
    expect((screen.getByLabelText("First name") as HTMLInputElement).value).toBe("Amaka");
  });

  it("does not save without a surname", () => {
    currentUser = { id: "u3", role: "customer", email: "c@example.com", full_name: "Amaka Okafor" };
    render(<ProfileForm />);
    fireEvent.change(screen.getByLabelText("Surname"), { target: { value: " " } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(updateProfile).not.toHaveBeenCalled();
    expect(screen.getByText("Enter your surname.")).toBeTruthy();
  });
});
