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

/** An in-app call (voice over the internet; nobody's number is used). */
export type AppCallStatus = "ringing" | "active" | "ended" | "declined" | "cancelled" | "missed";

export interface AppCall {
  call_id: string;
  status: AppCallStatus;
  order_id: string;
  order_number: string | null;
  other_party_name: string;
  you_are: "caller" | "callee";
  started_at: string | null;
  answered_at: string | null;
}

/** Returned when starting or answering: a short-lived pass for this call's private room. */
export interface AppCallJoin extends AppCall {
  token: string;
  url: string;
}
