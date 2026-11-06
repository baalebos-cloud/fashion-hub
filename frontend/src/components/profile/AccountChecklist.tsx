import { useState } from "react";
import { useAuthStore } from "@/store/auth.store";
import { authApi } from "@/api/auth.api";
import { ProfilePhoto } from "@/components/profile/ProfilePhoto";
import { PHOTO_REQUIRED_ROLES } from "@/constants/roles";

/**
 * Shown above every dashboard page until the account is complete:
 * confirm the email address, and (riders, vendors, tailors, designers) add a profile photo.
 */
export function AccountChecklist() {
  const user = useAuthStore((s) => s.user);
  const refreshUser = useAuthStore((s) => s.refreshUser);
  const [sent, setSent] = useState<"idle" | "sending" | "sent" | "error">("idle");

  if (!user || user.role === "admin") return null;
  const needsEmail = !user.is_email_verified;
  const needsPhoto = PHOTO_REQUIRED_ROLES.has(user.role) && !user.profile_photo_url;
  if (!needsEmail && !needsPhoto) return null;

  async function resend() {
    if (!user) return;
    setSent("sending");
    try {
      await authApi.resendVerification(user.email);
      setSent("sent");
    } catch {
      setSent("error");
    }
  }

  return (
    <div className="mb-6 flex flex-col gap-3">
      {needsEmail && (
        <div role="status" className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-brass/40 bg-muslin px-4 py-3 text-sm">
          <p className="text-ink">
            Confirm your email address. We sent a link to <span className="font-medium">{user.email}</span>.
          </p>
          {sent === "sent" ? <span className="text-ink-soft">New link sent. Check your inbox and spam folder.</span> : (
            <button type="button" onClick={() => void resend()} disabled={sent === "sending"}
              className="font-medium text-brass-deep underline disabled:opacity-50">
              {sent === "sending" ? "Sending…" : "Send a new link"}
            </button>
          )}
          {sent === "error" && <p role="alert" className="w-full text-thread">Couldn't send right now. Try again in a minute.</p>}
        </div>
      )}
      {needsPhoto && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-thread/30 bg-paper px-4 py-3 text-sm" role="region" aria-label="Profile photo required">
          <div className="min-w-0">
            <p className="font-medium text-ink">Add a profile photo</p>
            <p className="text-ink-soft">
              Customers meet you in person, so a clear photo of your face{user.role === "vendor" ? " or your shop" : ""} is required
              before you can be verified.
            </p>
          </div>
          <ProfilePhoto currentUrl={null} onUploaded={() => void refreshUser()} />
        </div>
      )}
    </div>
  );
}
