import { useEffect, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { appReturnLink } from "@/lib/payments/return-url";

/** After paying inside the phone app, the payment provider lands here (in the phone's browser), and
 * this page hands the person back to the Tailora app. Nothing is confirmed on this page. */
export default function PaymentAppReturn() {
  const [params] = useSearchParams();
  const link = useMemo(() => appReturnLink(params.get("for"), params), [params]);

  useEffect(() => {
    if (link) window.location.href = link;
  }, [link]);

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center gap-4 px-5 text-center">
      <h1 className="font-display text-2xl text-ink">Payment finished</h1>
      <p className="text-sm leading-6 text-ink-soft">
        Return to the Tailora app to see your payment confirmed. If the app doesn't open, open it yourself
        and check your order; the payment is recorded either way.
      </p>
      {link && (
        <a href={link} className="rounded-control bg-indigo px-5 py-3 text-[15px] font-medium text-surface">
          Return to the Tailora app
        </a>
      )}
    </main>
  );
}
