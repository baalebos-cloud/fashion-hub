export type ReferralStatus = "pending" | "qualified" | "paid";

export interface Referral {
  id: string;
  referred_user_id: string;
  status: ReferralStatus;
  commission_amount?: number | null;
  commission_currency?: string | null;
  qualified_at?: string | null;
  paid_at?: string | null;
}

export interface ReferralSummary {
  total_referred: number;
  qualified_count: number;
  total_earned: number;
  total_paid: number;
  referrals: Referral[];
}

export interface ReferralCode {
  referral_code: string;
  referral_link: string;
}
