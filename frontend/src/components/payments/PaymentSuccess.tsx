import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function PaymentSuccess({ ordersPath }: { ordersPath: string }) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center gap-4 py-12 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#e5f3ea] text-[#256a3f]">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <h1 className="font-display text-xl text-ink">Payment successful</h1>
      <p className="text-sm text-ink-soft">Your invoice will be ready shortly.</p>
      <Link to={ordersPath}>
        <Button>View my orders</Button>
      </Link>
    </div>
  );
}
