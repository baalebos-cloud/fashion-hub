import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/** Top-level crash guard, mounted once around the router in App.tsx.
 * Catches render-time exceptions in any page/component beneath it and
 * shows a recovery screen instead of a blank white page. Does not (and
 * cannot) catch errors from async code like a rejected fetch — those are
 * handled per-call via ApiError (see lib/api/errors.ts). */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("Unhandled render error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muslin px-4 text-center">
          <h1 className="font-display text-2xl text-ink">Something went wrong</h1>
          <p className="max-w-sm text-sm text-ink-soft">
            We hit an unexpected error. Reloading usually fixes it — if it keeps happening, please contact support.
          </p>
          <Button onClick={() => window.location.reload()}>Reload the page</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
