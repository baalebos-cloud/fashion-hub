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
vi.mock("@/components/verification/SelfieCapture", () => ({
  SelfieCapture: ({ onUploaded }: { onUploaded: (key: string) => void }) => <button type="button" onClick={() => onUploaded("kyc/u1/selfie.jpg")}>Take selfie</button>,
}));
vi.mock("@/api/verification.api", () => ({
  verificationApi: { queue: vi.fn(), review: vi.fn(), loadDocument: vi.fn(), checkDocument: vi.fn(), openReviewWindow: vi.fn() },
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
    expect(submit.disabled).toBe(true); // no selfie yet
    fireEvent.click(screen.getByRole("button", { name: "Take selfie" }));
    expect(submit.disabled).toBe(false);
    fireEvent.click(submit);
    await waitFor(() => expect(kyc.submit).toHaveBeenCalledWith(expect.objectContaining({
      nin_number: "70123456789", date_of_birth: "1990-04-12", selfie_storage_key: "kyc/u1/selfie.jpg" })));
  });

  it("says when the person was verified straight away", () => {
    kyc.status = { status: "verified", auto_approved: true, nin_verified_full_name: "KEMI ABOSEDE ADEYEMI" };
    render(<KYCForm />);
    expect(screen.getByText(/verified straight away/)).toBeTruthy();
    expect(screen.getByText("KEMI ABOSEDE ADEYEMI")).toBeTruthy();
  });
});

describe("result for the applicant", () => {
  it("lists what was checked and why it's under review", () => {
    kyc.status = { status: "under_review", result_checks: [
      { key: "name_matches", label: "Your name matches your NIN record", passed: true },
      { key: "selfie_matches_nin", label: "Your selfie matches the photo on your NIN record", passed: false },
    ], document_note: "Tailora checked your NIN slip: the name matches your account." };
    render(<KYCForm />);
    expect(screen.getByText("Tailora's verification result")).toBeTruthy();
    expect(screen.getByText(/Your selfie matches the photo on your NIN record/).textContent).toMatch(/didn't pass/);
    expect(screen.getByText(/Tailora checked your NIN slip/)).toBeTruthy();
    expect(screen.getByText(/why a person is reviewing/)).toBeTruthy();
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

describe("admin business queue", () => {
  it("lists the business rules that stopped automatic approval", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([{ id: "b1", status: "under_review", submitted_at: new Date().toISOString(),
      applicant_name: "Ada Obi", applicant_role: "vendor", documents: [], official_name: "LACE WORLD LIMITED", name_match: true,
      registry_checked: true, business_name: "Lace World", registration: "RC 1234567",
      auto_checks: { record_found: true, company_active: true, business_name_matches: true, identity_verified: true,
        owner_listed: false, profile_photo: true, registration_not_used_elsewhere: true } }]);
    render(<VerificationQueue kind="kyb" />);
    expect(await screen.findByText("Not approved automatically because:")).toBeTruthy();
    expect(screen.getByText("Owner is listed as a director, proprietor or shareholder: no")).toBeTruthy();
    expect(screen.queryByText(/Company is active/)).toBeNull();
  });
});

describe("Tailora's document check in the identity queue", () => {
  const base = { id: "k2", status: "under_review" as const, submitted_at: new Date().toISOString(),
    applicant_name: "Oluwapelumi Oluwapemi", applicant_role: "designer", documents: [{ id: "d1", type: "nin" }],
    official_name: null, name_match: null, registry_checked: false };

  it("shows the note, pre-fills it for the applicant, and explains the authenticator code", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([{ ...base, document_checked: true, document_note: "Tailora checked your NIN slip: the name matches your account." }]);
    render(<VerificationQueue kind="kyc" />);
    expect(await screen.findByText("Tailora's document check")).toBeTruthy();
    expect((screen.getByLabelText(/Note to applicant/) as HTMLTextAreaElement).value).toMatch(/the name matches your account/);
    expect(screen.getByText(/asks for the 6-digit code from your authenticator app/)).toBeTruthy();
  });

  it("runs the check on an older submission", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([base]);
    vi.mocked(verificationApi.checkDocument).mockResolvedValue({ passed: false, checked: true,
      checks: { document_readable: true, document_name_matches: false },
      document_note: "Tailora checked your document: the name on the NIN slip (ADA OBI) doesn't match." });
    render(<VerificationQueue kind="kyc" />);
    fireEvent.click(await screen.findByRole("button", { name: "Check document with Tailora" }));
    expect((await screen.findAllByText(/the name on the NIN slip \(ADA OBI\)/)).length).toBeGreaterThan(0);
    expect(screen.getByText("Name on the document matches the account: no")).toBeTruthy();
    expect(verificationApi.checkDocument).toHaveBeenCalledWith("k2");
  });
});

it("doesn't put a 'couldn't check' note into the message to the applicant, and offers a retry", async () => {
  vi.mocked(verificationApi.queue).mockResolvedValue([{ id: "k3", status: "under_review", submitted_at: new Date().toISOString(),
    applicant_name: "Bisi Ade", applicant_role: "tailor", documents: [{ id: "d1", type: "nin" }], official_name: null,
    name_match: null, registry_checked: false, document_checked: false,
    document_note: "Tailora couldn't check the document automatically (Groq: HTTP 404, the model wasn't found). Compare it by hand." }]);
  render(<VerificationQueue kind="kyc" />);
  expect(await screen.findByText(/Groq: HTTP 404/)).toBeTruthy();
  expect((screen.getByLabelText(/Note to applicant/) as HTMLTextAreaElement).value).toBe("");
  expect(screen.getByRole("button", { name: "Try the check again" })).toBeTruthy();
});

describe("face match in the identity queue", () => {
  it("shows the selfie and each face match result", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([{ id: "k9", status: "under_review", submitted_at: new Date().toISOString(),
      applicant_name: "Tunde Bakare", applicant_role: "tailor", documents: [{ id: "d1", type: "nin" }, { id: "d2", type: "selfie" }],
      official_name: "TUNDE BAKARE", name_match: true, registry_checked: true,
      auto_checks: { record_found: true, selfie_matches_nin: true, profile_photo_matches_nin: false },
      face: { selfie_confidence: 95.5, profile_photo_confidence: 32.0 } }]);
    render(<VerificationQueue kind="kyc" />);
    expect(await screen.findByRole("button", { name: "View selfie" })).toBeTruthy();
    expect(screen.getByText("Profile photo matches the NIN record photo: no")).toBeTruthy();
    expect(screen.getByText(/Selfie 95.5%/)).toBeTruthy();
  });
});
