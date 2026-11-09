import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const { prepareImage, uploadFile, patch } = vi.hoisted(() => ({
  prepareImage: vi.fn(), uploadFile: vi.fn(), patch: vi.fn(),
}));
vi.mock("@/lib/media/prepare-image", () => ({ prepareImage }));
vi.mock("@/lib/storage/file-storage", () => ({ uploadFile }));
vi.mock("@/lib/api/client", () => ({ apiClient: { patch } }));
vi.mock("@/components/ui/button", () => ({
  Button: ({ children, isLoading, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { isLoading?: boolean }) =>
    <button {...props} disabled={isLoading}>{children}</button>,
}));

import { TailorProfilePhoto } from "@/components/profile/TailorProfilePhoto";

describe("tailor-only profile photo upload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    prepareImage.mockImplementation(async (file: File) => file);
    uploadFile.mockResolvedValue({ url: "/api/v1/media/files/123" });
    patch.mockResolvedValue({});
  });

  it("reduces avatar resolution, uploads, persists, then refreshes the profile", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<TailorProfilePhoto onUploaded={refresh} />);
    const photo = new File(["jpeg"], "portrait.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Choose tailor profile photo"), { target: { files: [photo] } });
    await waitFor(() => expect(refresh).toHaveBeenCalledWith("/api/v1/media/files/123"));
    expect(prepareImage).toHaveBeenCalledWith(photo, 1024);
    expect(uploadFile).toHaveBeenCalledWith("/media/upload?purpose=avatar", photo);
    expect(patch).toHaveBeenCalledWith("/users/me", { profile_photo_url: "/api/v1/media/files/123" });
    expect(screen.getByRole("status").textContent).toMatch(/updated/i);
  });

  it("does not save a profile when the upload fails and shows the failure", async () => {
    uploadFile.mockRejectedValue(new Error("Upload failed"));
    render(<TailorProfilePhoto onUploaded={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Choose tailor profile photo"), {
      target: { files: [new File(["jpeg"], "portrait.jpg", { type: "image/jpeg" })] },
    });
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(patch).not.toHaveBeenCalled();
  });

  it("refuses non-image files before sending a request", async () => {
    render(<TailorProfilePhoto onUploaded={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Choose tailor profile photo"), {
      target: { files: [new File(["text"], "notes.txt", { type: "text/plain" })] },
    });
    expect(screen.getByRole("alert").textContent).toMatch(/choose a photo/i);
    expect(uploadFile).not.toHaveBeenCalled();
  });

  it("reports a profile-save failure instead of claiming success", async () => {
    patch.mockRejectedValue(new Error("Save failed"));
    const refresh = vi.fn();
    render(<TailorProfilePhoto onUploaded={refresh} />);
    fireEvent.change(screen.getByLabelText("Choose tailor profile photo"), {
      target: { files: [new File(["jpeg"], "portrait.jpg", { type: "image/jpeg" })] },
    });
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
    expect(refresh).not.toHaveBeenCalled();
  });
});
