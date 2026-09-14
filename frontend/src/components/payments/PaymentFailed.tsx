import { Button } from "@/components/ui/button";

export function PaymentFailed({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center gap-4 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#fbeceA] text-thread">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
        </svg>
      </div>
      <h1 className="font-display text-xl text-ink">Payment failed</h1>
      <p className="text-sm text-ink-soft">No charge was made. You can try again.</p>
      <Button onClick={onRetry}>Try again</Button>
    </div>
  );
}
