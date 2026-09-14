import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { validateSignUp } from "@/lib/validation/auth";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { authRoutes } from "@/config/routes.config";
import { ROLE_LABELS } from "@/constants/roles";
import type { UserRole } from "@/types/auth";

const SIGNUP_ROLES: UserRole[] = ["customer", "tailor", "designer", "vendor", "delivery_partner"];

export function SignupForm() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("customer");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errors = validateSignUp({ email, password, fullName });
    if (errors.length > 0) {
      setFieldErrors(Object.fromEntries(errors.map((err) => [err.field, err.message])));
      return;
    }
    setFieldErrors({});
    setFormError(null);
    setIsSubmitting(true);
    try {
      await signUp({ email, password, full_name: fullName, role });
      navigate(authRoutes.login, { state: { justSignedUp: true } });
    } catch (err) {
      setFormError(getDisplayErrorMessage(err, "Could not create your account."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Create your account</h1>

      <div>
        <label htmlFor="fullName" className="mb-1.5 block text-sm font-medium text-ink">Full name</label>
        <Input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} error={fieldErrors.fullName} required />
      </div>

      <div>
        <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink">Email</label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={fieldErrors.email} required />
      </div>

      <div>
        <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink">Password</label>
        <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} error={fieldErrors.password} required />
        {fieldErrors.password && <p className="mt-1 text-xs text-thread">{fieldErrors.password}</p>}
      </div>

      <div>
        <label htmlFor="role" className="mb-1.5 block text-sm font-medium text-ink">I am a…</label>
        <Select id="role" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          {SIGNUP_ROLES.map((r) => (
            <option key={r} value={r}>{ROLE_LABELS[r]}</option>
          ))}
        </Select>
      </div>

      {formError && <p className="text-sm text-thread">{formError}</p>}

      <Button type="submit" isLoading={isSubmitting} className="w-full">Create account</Button>

      <p className="text-center text-sm text-ink-soft">
        Already have an account? <Link to={authRoutes.login} className="text-brass-deep hover:underline">Log in</Link>
      </p>
    </form>
  );
}
