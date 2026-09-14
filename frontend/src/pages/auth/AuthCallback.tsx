/**
 * AuthCallback
 *
 * Landing page for any external auth redirect flow (e.g. a future OAuth
 * provider). The current scaffold only supports email/password auth
 * (see backend/docs/authentication.md), so this is a placeholder for
 * when/if a third-party login provider is added.
 *
 * STATUS: scaffold stub.
 */
export default function AuthCallback() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-sm text-ink-soft">Completing sign in…</p>
    </div>
  );
}
