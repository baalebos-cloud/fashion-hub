import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { authApi } from "@/api/auth.api";
import { authRoutes } from "@/config/routes.config";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"verifying" | "success" | "error">("verifying");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      return;
    }
    authApi
      .verifyEmail(token)
      .then(() => setStatus("success"))
      .catch(() => setStatus("error"));
  }, [searchParams]);

  if (status === "verifying") return <LoadingScreen label="Verifying your email…" />;

  if (status === "success") {
    return (
      <div className="text-center">
        <h1 className="font-display text-xl text-ink">Email verified</h1>
        <p className="mt-2 text-sm text-ink-soft">You&apos;re all set.</p>
        <Link to={authRoutes.login} className="mt-4 inline-block text-sm text-brass-deep hover:underline">
          Continue to log in
        </Link>
      </div>
    );
  }

  return <ResendVerification />;
}

/** Expired or broken link: send a fresh one to the address the person types. */
function ResendVerification() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("sending");
    try {
      await authApi.resendVerification(email.trim());
      setState("sent");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="text-center">
      <h1 className="font-display text-xl text-ink">This link has expired</h1>
      {state === "sent" ? (
        <p className="mt-2 text-sm text-ink-soft" role="status">
          If that email has an unconfirmed Tailora account, a new link is on its way. Check your inbox and spam folder.
        </p>
      ) : (
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3 text-left">
          <p className="text-sm text-ink-soft">Enter your email and we'll send you a new confirmation link.</p>
          <label htmlFor="resend-email" className="text-sm font-medium text-ink">Email address</label>
          <input id="resend-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border border-line bg-paper px-3 py-2 text-sm" placeholder="you@example.com" />
          <button type="submit" disabled={state === "sending" || !email.includes("@")}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-medium text-paper disabled:opacity-50">
            {state === "sending" ? "Sending…" : "Send a new link"}
          </button>
          {state === "error" && <p role="alert" className="text-sm text-thread">Couldn't send right now. Try again in a minute.</p>}
        </form>
      )}
      <Link to={authRoutes.login} className="mt-4 inline-block text-sm text-brass-deep hover:underline">Back to sign in</Link>
    </div>
  );
}
