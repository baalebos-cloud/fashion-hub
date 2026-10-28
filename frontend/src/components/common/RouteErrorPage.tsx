import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom";
import { publicRoutes } from "@/config/routes.config";

/** User-facing fallback for unexpected route errors; never show stack traces. */
export function RouteErrorPage() {
  const error = useRouteError();
  const missing = isRouteErrorResponse(error) && error.status === 404;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muslin px-5 text-center">
      <h1 className="font-display text-2xl text-ink">
        {missing ? "Page not found" : "We couldn't open this page"}
      </h1>
      <p className="max-w-md text-sm leading-6 text-ink-soft">
        {missing
          ? "The page may have moved or the address may be incorrect."
          : "An unexpected problem stopped this page from loading. You can return home or try again."}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          to={publicRoutes.home}
          className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-paper hover:opacity-90"
        >
          Go to homepage
        </Link>
        {!missing && (
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-lg border border-line bg-paper px-5 py-2.5 text-sm font-medium text-ink"
          >
            Try again
          </button>
        )}
      </div>
    </main>
  );
}
