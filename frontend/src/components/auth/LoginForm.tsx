import { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { validateLogIn } from "@/lib/validation/auth";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authRoutes } from "@/config/routes.config";
import { ROLE_HOME_PATH } from "@/constants/roles";

export function LoginForm() {
  const { logIn, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errors = validateLogIn({ email, password });
    if (errors.length > 0) {
      setFieldErrors(Object.fromEntries(errors.map((err) => [err.field, err.message])));
      return;
    }
    setFieldErrors({});
    setFormError(null);
    setIsSubmitting(true);
    try {
      await logIn({ email, password });
      const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? (user ? ROLE_HOME_PATH[user.role] : "/");
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setFormError(getDisplayErrorMessage(err, "Incorrect email or password."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <h1 className="font-display text-xl text-ink">Welcome back</h1>

      <div>
        <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink">Email</label>
        <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={fieldErrors.email} required />
        {fieldErrors.email && <p className="mt-1 text-xs text-thread">{fieldErrors.email}</p>}
      </div>

      <div>
        <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink">Password</label>
        <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} error={fieldErrors.password} required />
        {fieldErrors.password && <p className="mt-1 text-xs text-thread">{fieldErrors.password}</p>}
        <Link to={authRoutes.forgotPassword} className="mt-1.5 inline-block text-xs text-brass-deep hover:underline">
          Forgot password?
        </Link>
      </div>

      {formError && <p className="text-sm text-thread">{formError}</p>}

      <Button type="submit" isLoading={isSubmitting} className="w-full">Log in</Button>

      <p className="text-center text-sm text-ink-soft">
        Don&apos;t have an account? <Link to={authRoutes.signup} className="text-brass-deep hover:underline">Sign up</Link>
      </p>
    </form>
  );
}
