import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "@/hooks/use-auth";
import { validateSignUp } from "@/lib/validation/auth";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authRoutes } from "@/config/routes.config";
import { ROLE_LABELS } from "@/constants/roles";
import { cn } from "@/lib/utils/cn";
import type { UserRole } from "@/types/auth";

const SIGNUP_ROLES: { role: UserRole; emoji: string }[] = [
  { role: "customer", emoji: "🛍️" },
  { role: "tailor", emoji: "🧵" },
  { role: "designer", emoji: "✏️" },
  { role: "vendor", emoji: "🏪" },
  { role: "delivery_partner", emoji: "🚚" },
];

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg width="18" height="18" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 7.61 17 4.5 12 4.5zm0 12.5a5 5 0 1 1 0-10 5 5 0 0 1 0 10zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6z" fill="currentColor"/>
    </svg>
  ) : (
    <svg width="18" height="18" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75C21.27 7.61 17 4.5 12 4.5c-1.27 0-2.49.2-3.64.57l2.17 2.17C11.21 7.1 11.6 7 12 7zM2 4.27l2.28 2.28.46.46A11.8 11.8 0 0 0 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55A2.82 2.82 0 0 0 9 12a3 3 0 0 0 3 3c.22 0 .44-.03.65-.07l1.55 1.55A4.96 4.96 0 0 1 12 17a5 5 0 0 1-5-5c0-.82.22-1.6.53-2.2zm4.31-.78 3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z" fill="currentColor"/>
    </svg>
  );
}

export function SignupForm() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const referralCode = searchParams.get("ref") ?? undefined;

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      await signUp({ email, password, full_name: fullName, role, referral_code: referralCode });
      navigate(authRoutes.login, { state: { justSignedUp: true } });
    } catch (err) {
      setFormError(getDisplayErrorMessage(err, "Could not create your account."));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5" noValidate>
      <div className="mb-1">
        <h1 className="font-display text-2xl text-ink">Create your account</h1>
        <p className="mt-1 text-sm text-ink-soft">Join Tailora — it’s free.</p>
      </div>

      {referralCode && (
        <p className="rounded-lg bg-brass/10 px-3 py-2 text-xs text-ink-soft">
          Signing up with referral code{" "}
          <span className="font-medium text-ink">{referralCode}</span>
        </p>
      )}

      {/* Role picker */}
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-ink">I am a…</legend>
        <div className="grid grid-cols-5 gap-1.5">
          {SIGNUP_ROLES.map(({ role: r, emoji }) => (
            <label
              key={r}
              className={cn(
                "flex cursor-pointer flex-col items-center gap-1 rounded-xl border p-2 text-center transition-colors",
                role === r
                  ? "border-brass bg-brass/10 text-ink"
                  : "border-line bg-paper text-ink-soft hover:border-brass/50"
              )}
            >
              <input
                type="radio"
                name="role"
                value={r}
                checked={role === r}
                onChange={() => setRole(r)}
                className="sr-only"
              />
              <span className="text-lg" aria-hidden="true">{emoji}</span>
              <span className="text-[10px] font-medium leading-tight">
                {ROLE_LABELS[r].split(" ")[0]}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="fullName" className="text-sm font-medium text-ink">Full name</label>
        <Input
          id="fullName"
          autoComplete="name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          error={fieldErrors.fullName}
          placeholder="Ada Okonkwo"
          required
        />
        {fieldErrors.fullName && (
          <p className="text-xs text-thread" role="alert">{fieldErrors.fullName}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="email" className="text-sm font-medium text-ink">Email address</label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
          placeholder="you@example.com"
          required
        />
        {fieldErrors.email && (
          <p className="text-xs text-thread" role="alert">{fieldErrors.email}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium text-ink">Password</label>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={fieldErrors.password}
            className="pr-10"
            required
          />
          <button
            type="button"
            aria-label={showPassword ? "Hide password" : "Show password"}
            onClick={() => setShowPassword((v) => !v)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
          >
            <EyeIcon open={showPassword} />
          </button>
        </div>
        {fieldErrors.password && (
          <p className="text-xs text-thread" role="alert">{fieldErrors.password}</p>
        )}
      </div>

      {formError && (
        <p className="rounded-lg bg-thread/10 px-3 py-2 text-sm text-thread" role="alert">
          {formError}
        </p>
      )}

      <Button type="submit" isLoading={isSubmitting} className="w-full" size="lg">
        Create account
      </Button>

      <p className="text-center text-sm text-ink-soft">
        Already have an account?{" "}
        <Link to={authRoutes.login} className="font-medium text-brass-deep hover:underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
