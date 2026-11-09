import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import qrcode from "qrcode-generator";
import { authApi, type AdminSignInStep } from "@/api/auth.api";
import { useAuthStore } from "@/store/auth.store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import { adminRoutes } from "@/config/routes.config";

function QrCode({ value }: { value: string }) {
  const svg = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(value);
    qr.make();
    return qr.createSvgTag({ cellSize: 5, margin: 2, scalable: true });
  }, [value]);
  // Generated locally from the setup link: no third-party image service sees the secret.
  return <div className="mx-auto w-48 rounded-lg bg-white p-2" role="img" aria-label="Authenticator setup QR code"
    dangerouslySetInnerHTML={{ __html: svg }} />;
}

/**
 * Two-step admin sign-in: password, then a six-digit code from an authenticator app.
 * The first sign-in shows a QR code to set the app up. Not linked from the public site.
 */
export default function AdminLogin() {
  const navigate = useNavigate();
  const location = useLocation();
  const completeSignIn = useAuthStore((s) => s.completeSignIn);
  // Coming from the regular sign-in page keeps the email typed there.
  const [email, setEmail] = useState(() => (location.state as { email?: string } | null)?.email ?? "");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<AdminSignInStep | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const robots = document.createElement("meta");
    robots.name = "robots";
    robots.content = "noindex, nofollow";
    document.head.append(robots);
    document.title = "Admin sign-in · Tailora";
    return () => robots.remove();
  }, []);

  async function submitPassword(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setStep(await authApi.adminLogIn(email.trim(), password));
      setPassword("");
    } catch (err) {
      setError(getDisplayErrorMessage(err, "Invalid email, password or code."));
    } finally {
      setBusy(false);
    }
  }

  async function submitCode(event: FormEvent) {
    event.preventDefault();
    if (!step) return;
    setBusy(true);
    setError(null);
    try {
      await completeSignIn(await authApi.adminVerify(step.challenge, code));
      navigate(adminRoutes.dashboard, { replace: true });
    } catch (err) {
      setCode("");
      const message = getDisplayErrorMessage(err, "Invalid email, password or code.");
      setError(message);
      if (/expired|start again/i.test(message)) setStep(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-4 py-12">
      <div className="w-full max-w-sm rounded-card bg-paper p-6 shadow-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brass-deep">Tailora admin</p>
        {!step ? (
          <form onSubmit={submitPassword} className="mt-2 flex flex-col gap-4" noValidate>
            <h1 className="font-display text-2xl text-ink">Sign in</h1>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="admin-email" className="text-sm font-medium text-ink">Email address</label>
              <Input id="admin-email" type="email" autoComplete="username" value={email} required
                onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="admin-password" className="text-sm font-medium text-ink">Password</label>
              <Input id="admin-password" type="password" autoComplete="current-password" value={password} required
                onChange={(e) => setPassword(e.target.value)} />
            </div>
            <Button type="submit" isLoading={busy} disabled={busy || !email || !password}>Continue</Button>
          </form>
        ) : (
          <form onSubmit={submitCode} className="mt-2 flex flex-col gap-4" noValidate>
            {step.step === "enroll" ? (
              <>
                <h1 className="font-display text-2xl text-ink">Set up your authenticator</h1>
                <p className="text-sm text-ink-soft">
                  Scan this with Google Authenticator, Microsoft Authenticator, Authy or 1Password, then enter the
                  six-digit code it shows. You'll need the app every time you sign in.
                </p>
                {step.otpauth_uri && <QrCode value={step.otpauth_uri} />}
                {step.secret && (
                  <div className="rounded-lg bg-muslin px-3 py-2 text-xs text-ink">
                    <p className="text-ink-soft">Can't scan? Enter this key in the app:</p>
                    <p className="mt-1 break-all font-mono text-sm tracking-wider" data-testid="totp-secret">{step.secret}</p>
                  </div>
                )}
              </>
            ) : (
              <>
                <h1 className="font-display text-2xl text-ink">Enter your code</h1>
                <p className="text-sm text-ink-soft">Open your authenticator app and enter the six-digit Tailora Admin code.</p>
              </>
            )}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="admin-code" className="text-sm font-medium text-ink">Six-digit code</label>
              <Input id="admin-code" inputMode="numeric" autoComplete="one-time-code" value={code} maxLength={6}
                className="tracking-[0.4em]" onChange={(e) => setCode(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))} />
            </div>
            <Button type="submit" isLoading={busy} disabled={busy || code.length !== 6}>Sign in</Button>
            <button type="button" className="text-xs text-ink-soft underline" onClick={() => { setStep(null); setCode(""); setError(null); }}>
              Start again
            </button>
          </form>
        )}
        {error && <p role="alert" className="mt-4 text-sm text-thread">{error}</p>}
        <p className="mt-6 text-xs text-ink-soft">Sign-ins to this page are recorded with IP address and device.</p>
      </div>
    </div>
  );
}
