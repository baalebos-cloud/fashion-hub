import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { KYCForm } from "@/components/verification/KYCForm";
import { VerificationQueue } from "@/components/verification/VerificationQueue";
import { verificationApi } from "@/api/verification.api";

const kyc = vi.hoisted(() => ({ status: null as unknown, submit: vi.fn() }));
vi.mock("@/hooks/use-kyc", () => ({ useKYC: () => ({ status: kyc.status, isLoading: false, submit: kyc.submit }) }));
vi.mock("@/hooks/use-timezone", () => ({ useTimezone: () => "Africa/Lagos" }));
vi.mock("@/components/verification/DocumentUpload", () => ({
  DocumentUpload: ({ onUploaded }: { onUploaded: (key: string) => void }) => <button type="button" onClick={() => onUploaded("kyc/id.jpg")}>Upload ID</button>,
}));
vi.mock("@/components/common/AddressMapPicker", () => ({ AddressMapPicker: () => null }));
vi.mock("@/api/verification.api", () => ({
  verificationApi: { queue: vi.fn(), review: vi.fn(), openDocument: vi.fn(), openReviewWindow: vi.fn() },
  hasReviewWindow: () => false, endReviewWindow: () => {},
}));
afterEach(() => { cleanup(); vi.clearAllMocks(); kyc.status = null; });

describe("NIN form", () => {
  it("needs the date of birth and sends it with the NIN", async () => {
    kyc.submit.mockResolvedValue({ status: "verified", auto_approved: true });
    render(<KYCForm />);
    fireEvent.change(screen.getByLabelText("National Identity Number (NIN)"), { target: { value: "70123456789" } });
    fireEvent.click(screen.getByRole("button", { name: "Upload ID" }));
    fireEvent.change(screen.getByLabelText("Street address"), { target: { value: "3 Allen Avenue" } });
    fireEvent.change(screen.getByLabelText("City / LGA"), { target: { value: "Ikeja" } });
    fireEvent.change(screen.getByLabelText("State"), { target: { value: "Lagos" } });
    const submit = screen.getAllByRole("button").find((b) => /submit|verify/i.test(b.textContent ?? "")) as HTMLButtonElement;
    expect(submit.disabled).toBe(true); // no date of birth yet
    fireEvent.change(screen.getByLabelText("Date of birth (as on your NIN)"), { target: { value: "1990-04-12" } });
    expect(submit.disabled).toBe(false);
    fireEvent.click(submit);
    await waitFor(() => expect(kyc.submit).toHaveBeenCalledWith(expect.objectContaining({ nin_number: "70123456789", date_of_birth: "1990-04-12" })));
  });

  it("says when the person was verified straight away", () => {
    kyc.status = { status: "verified", auto_approved: true, nin_verified_full_name: "KEMI ABOSEDE ADEYEMI" };
    render(<KYCForm />);
    expect(screen.getByText(/verified straight away/)).toBeTruthy();
    expect(screen.getByText("KEMI ABOSEDE ADEYEMI")).toBeTruthy();
  });
});

describe("admin identity queue", () => {
  it("lists the rules that stopped automatic approval", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([{ id: "k1", status: "under_review", submitted_at: new Date().toISOString(),
      applicant_name: "Kemi Adeyemi", applicant_role: "tailor", documents: [], official_name: "KEMI ADEYEMI", name_match: true,
      registry_checked: true, auto_checks: { record_found: true, name_matches: true, date_of_birth_matches: false, profile_photo: true, nin_not_used_elsewhere: false } }]);
    render(<VerificationQueue kind="kyc" />);
    expect(await screen.findByText("Not approved automatically because:")).toBeTruthy();
    expect(screen.getByText("Date of birth matches the NIN record: no")).toBeTruthy();
    expect(screen.getByText("NIN not used on another account: no")).toBeTruthy();
    expect(screen.queryByText(/Name matches the NIN record/)).toBeNull();
  });
});
