export type CallParty = "buyer" | "seller" | "rider";

export interface CallContact {
  party: CallParty;
  display_name: string;
  available: boolean;
  reason: string | null;
}

export interface StartedCall {
  call_id: string;
  status: string;
  callee_display_name: string;
  your_phone_ending: string | null;
}
