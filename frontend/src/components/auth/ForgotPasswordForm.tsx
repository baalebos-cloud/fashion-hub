import { useState, type FormEvent } from "react";
import { authApi } from "@/api/auth.api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSent, setIsSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await authApi.forgotPassword(email);
    } finally {
      setIsSubmitting(false);
      // Always show the same confirmation regardless of outcome — the
      // backend deliberately doesn't reveal whether the email exists
      // (see backend/docs/authentication.md), so the frontend shouldn't either.
      setIsSent(true);
    }
  }

  if (isSent) {
    return <p className="text-sm text-ink-soft">If an account with that email exists, we&apos;ve sent a reset link.</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Reset your password</h1>
      <div>
        <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink">Email</label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </div>
      <Button type="submit" isLoading={isSubmitting} className="w-full">Send reset link</Button>
    </form>
  );
}
