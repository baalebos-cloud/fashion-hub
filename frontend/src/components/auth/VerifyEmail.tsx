import { useEffect, useState } from "react";
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

  return (
    <div className="text-center">
      <h1 className="font-display text-xl text-ink">Verification link invalid</h1>
      <p className="mt-2 text-sm text-ink-soft">This link may have expired. Please request a new one from your account settings.</p>
    </div>
  );
}
