import { useEffect, useState } from "react";
import { referralsApi } from "@/api/referrals.api";
import { getDisplayErrorMessage } from "@/lib/utils/errors";
import type { ReferralCode, ReferralSummary } from "@/types/referral";

export function useReferrals() {
  const [code, setCode] = useState<ReferralCode | null>(null);
  const [summary, setSummary] = useState<ReferralSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([referralsApi.getMyCode(), referralsApi.getMySummary()])
      .then(([codeResult, summaryResult]) => {
        setCode(codeResult);
        setSummary(summaryResult);
      })
      .catch((err) => setError(getDisplayErrorMessage(err)))
      .finally(() => setIsLoading(false));
  }, []);

  return { code, summary, isLoading, error };
}
