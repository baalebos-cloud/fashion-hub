import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "@/api/auth.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authRoutes } from "@/config/routes.config";

export function ResetPasswordForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") ?? "";

  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await authApi.resetPassword(token, newPassword);
      navigate(authRoutes.login, { state: { passwordWasReset: true } });
    } catch (err) {
      setError(getDisplayErrorMessage(err, "This reset link may have expired."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Choose a new password</h1>
      <div>
        <label htmlFor="newPassword" className="mb-1.5 block text-sm font-medium text-ink">New password</label>
        <Input id="newPassword" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} />
      </div>
      {error && <p className="text-sm text-thread">{error}</p>}
      <Button type="submit" isLoading={isSubmitting} className="w-full">Reset password</Button>
    </form>
  );
}
