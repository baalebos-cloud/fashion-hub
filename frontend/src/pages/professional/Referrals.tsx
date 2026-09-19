import { useReferrals } from "@/hooks/use-referrals";
import { ReferralCodeCard } from "@/components/referrals/ReferralCodeCard";
import { ReferralStats } from "@/components/referrals/ReferralStats";
import { ReferralList } from "@/components/referrals/ReferralList";
import { LoadingScreen } from "@/components/common/LoadingScreen";

export default function Referrals() {
  const { code, summary, isLoading, error } = useReferrals();

  if (isLoading) return <LoadingScreen label="Loading your referrals…" />;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-xl text-ink">Referrals</h1>
      {error && <p className="text-sm text-thread">{error}</p>}
      {code && <ReferralCodeCard code={code} />}
      {summary && (
        <>
          <ReferralStats summary={summary} />
          <ReferralList referrals={summary.referrals} />
        </>
      )}
    </div>
  );
}
