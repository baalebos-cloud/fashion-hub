export type PaymentStatus = "initialized" | "pending" | "successful" | "failed" | "reversed";

export interface Payment {
  id: string;
  order_id: string;
  provider: string;
  provider_reference: string;
  amount: number;
  currency: string;
  status: PaymentStatus;
  paid_at?: string | null;
}

export interface InitializePaymentResponse {
  authorization_url: string;
  provider_reference: string;
}
