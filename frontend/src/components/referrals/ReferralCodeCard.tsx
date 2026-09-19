import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import type { ReferralCode } from "@/types/referral";

export function ReferralCodeCard({ code }: { code: ReferralCode }) {
  const { showToast } = useToast();
  const [isCopying, setIsCopying] = useState(false);

  async function handleCopy() {
    setIsCopying(true);
    try {
      await navigator.clipboard.writeText(code.referral_link);
      showToast("Referral link copied.", "success");
    } catch {
      showToast("Couldn't copy — copy it manually instead.", "error");
    } finally {
      setIsCopying(false);
    }
  }

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <div className="text-xs font-medium uppercase tracking-wide text-ink-soft">Your referral code</div>
        <div className="mt-1 font-display text-2xl text-ink">{code.referral_code}</div>
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-line bg-muslin px-3 py-2 text-sm text-ink-soft">
        <span className="flex-1 truncate">{code.referral_link}</span>
        <Button size="sm" variant="secondary" onClick={handleCopy} isLoading={isCopying}>
          Copy link
        </Button>
      </div>
      <p className="text-xs text-ink-soft">
        Share this with other tailors, designers, or vendors. You earn a commission once someone who signs up with
        your link completes their first paid order — not just for signing up.
      </p>
    </Card>
  );
}
