import { useState, type FormEvent } from "react";
import { authApi } from "@/api/auth.api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    setError(false);
    try {
      await authApi.forgotPassword(email);
      setIsSent(true);
    } catch {
      // A network outage is not successful delivery; use the same message
      // regardless of whether this email belongs to an account.
      setError(true);
    } finally {
      setIsSubmitting(false);
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
      {error && <p role="alert" className="text-sm text-thread">Unable to request a reset link right now. Please try again.</p>}
      <Button type="submit" isLoading={isSubmitting} className="w-full">Send reset link</Button>
    </form>
  );
}
