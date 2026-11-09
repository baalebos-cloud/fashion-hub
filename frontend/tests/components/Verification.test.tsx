import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VerificationCenter } from "@/components/verification/VerificationCenter";
import { VerificationQueue } from "@/components/verification/VerificationQueue";
import { ApiError } from "@/lib/api/errors";
import { KYBForm } from "@/components/verification/KYBForm";
import { verificationApi } from "@/api/verification.api";
import { kybApi } from "@/api/kyb.api";

const reviewWindow = vi.hoisted(() => ({ open: false }));
vi.mock("@/api/verification.api", () => ({
  verificationApi: { me: vi.fn(), queue: vi.fn(), review: vi.fn(), loadDocument: vi.fn(), checkDocument: vi.fn(),
    openReviewWindow: vi.fn(async () => { reviewWindow.open = true; }) },
  hasReviewWindow: () => reviewWindow.open,
  endReviewWindow: () => { reviewWindow.open = false; },
}));
vi.mock("@/api/kyb.api", () => ({ kybApi: { submit: vi.fn(), getStatus: vi.fn() } }));
vi.mock("@/components/verification/KYCForm", () => ({ KYCForm: () => <p>KYC form</p> }));
vi.mock("@/components/verification/DocumentUpload", () => ({
  DocumentUpload: ({ onUploaded }: { onUploaded: (key: string) => void }) =>
    <button type="button" onClick={() => onUploaded("kyb/cert.pdf")}>Upload certificate</button>,
}));
vi.mock("@/lib/utils/errors", () => ({
  getDisplayErrorMessage: (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback),
}));

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("verification centre", () => {
  it("shows progress, the reviewer's note, and lets the person resubmit", async () => {
    vi.mocked(verificationApi.me).mockResolvedValue({
      role: "vendor", verified: false, next_step: "Fix the item marked 'Needs attention' and resubmit.",
      steps: [
        { key: "identity", title: "Identity (NIN)", required: true, status: "verified", rejection_reason: null, submitted_at: null, action: "kyc" },
        { key: "business", title: "Business registration (CAC)", required: true, status: "rejected",
          rejection_reason: "Certificate is cut off.", submitted_at: null, action: "kyb" },
      ],
    });
    vi.mocked(kybApi.getStatus).mockRejectedValue(new Error("404"));
    render(<VerificationCenter />);
    expect(await screen.findByText("Not verified yet")).toBeTruthy();
    expect(screen.getByText("1 of 2 required checks complete")).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toBe("Reviewer's note: Certificate is cut off.");
    expect(await screen.findByLabelText("CAC registration number")).toBeTruthy(); // rejected step opens its form
  });

  it("celebrates a verified profile", async () => {
    vi.mocked(verificationApi.me).mockResolvedValue({ role: "tailor", verified: true, next_step: "You're verified.", steps: [
      { key: "identity", title: "Identity (NIN)", required: true, status: "verified", rejection_reason: null, submitted_at: null, action: "kyc" }] });
    render(<VerificationCenter />);
    expect(await screen.findByText("You're verified")).toBeTruthy();
    expect(screen.getAllByText("Verified").length).toBeGreaterThan(0);
  });
});

describe("KYB form", () => {
  it("sends the business type with the registration number", async () => {
    vi.mocked(kybApi.getStatus).mockRejectedValue(new Error("404"));
    vi.mocked(kybApi.submit).mockResolvedValue({ status: "pending", verified_company_name: "ANKARA HOUSE", name_match: true });
    const onSubmitted = vi.fn();
    render(<KYBForm onSubmitted={onSubmitted} />);
    fireEvent.change(await screen.findByLabelText("Business type"), { target: { value: "BN" } });
    fireEvent.change(screen.getByLabelText("CAC registration number"), { target: { value: " BN 7654321 " } });
    fireEvent.click(screen.getByRole("button", { name: "Upload certificate" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit for review" }));
    await waitFor(() => expect(onSubmitted).toHaveBeenCalled());
    expect(kybApi.submit).toHaveBeenCalledWith("BN 7654321", "BN", ["kyb/cert.pdf"]);
    expect(await screen.findByText("ANKARA HOUSE")).toBeTruthy();
  });
});

describe("admin review queue", () => {
  const item = {
    id: "k1", status: "pending" as const, submitted_at: new Date().toISOString(), applicant_name: "Bisi Ola",
    applicant_role: "vendor", documents: [{ id: "doc1", type: "business_registration" }],
    official_name: "ZENITH OIL AND GAS LTD", name_match: false, registry_checked: true,
    business_name: "Fabric Hub", registration: "RC 1234567",
  };

  it("flags registry mismatches, requires a reason to reject, and approves", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([item]);
    vi.mocked(verificationApi.review).mockResolvedValue({ id: "k1", status: "verified" });
    render(<VerificationQueue kind="kyb" />);
    expect(await screen.findByText("Bisi Ola")).toBeTruthy();
    expect(screen.getByText(/doesn't match the name on the account/)).toBeTruthy();
    expect(screen.getByText("Vendor · Fabric Hub · RC 1234567")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(screen.getByRole("alert").textContent).toMatch(/Add a reason/);
    expect(verificationApi.review).not.toHaveBeenCalled();

    vi.mocked(verificationApi.loadDocument).mockResolvedValue({ url: "blob:doc1", type: "image/jpeg" });
    fireEvent.click(screen.getByRole("button", { name: "View document 1" }));
    expect(verificationApi.loadDocument).toHaveBeenCalledWith("doc1");
    // Shown inside the page (a new window doesn't open inside the phone apps).
    expect((await screen.findByRole("img", { name: /document 1/ })).getAttribute("src")).toBe("blob:doc1");
    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    fireEvent.change(screen.getByLabelText(/Note to applicant/), { target: { value: "Trading name; certificate checked." } });
    reviewWindow.open = false;
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    // No review window yet: ask for an authenticator code before deciding.
    expect(verificationApi.review).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Code from your authenticator app"), { target: { value: "12 34 56" } });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and approve" }));
    await waitFor(() => expect(verificationApi.review).toHaveBeenCalledWith("kyb", "k1", true, "Trading name; certificate checked."));
    expect(verificationApi.openReviewWindow).toHaveBeenCalledWith("123456");
  });

  it("decides straight away inside an open window, and asks again when it has ended", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([item]);
    reviewWindow.open = true;
    vi.mocked(verificationApi.review).mockRejectedValueOnce(new ApiError("ended", "step_up_required", 403, null));
    render(<VerificationQueue kind="kyb" />);
    fireEvent.change(await screen.findByLabelText(/Note to applicant/), { target: { value: "CAC certificate is cut off." } });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(verificationApi.review).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/review window has ended/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Confirm and reject" })).toBeTruthy();
    expect(reviewWindow.open).toBe(false);
  });

  it("warns when the registry couldn't be checked", async () => {
    vi.mocked(verificationApi.queue).mockResolvedValue([{ ...item, registry_checked: false, official_name: null, name_match: null }]);
    render(<VerificationQueue kind="kyc" />);
    expect(await screen.findByText(/NIN record couldn't be checked automatically/)).toBeTruthy();
  });
});
